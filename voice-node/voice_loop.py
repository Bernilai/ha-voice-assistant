#!/usr/bin/env python3
"""
voice_loop.py — голосовой цикл voice-node.

Слои:
  1. Wake-word   — wyoming-openwakeword (TCP :10400)
  2. STT         — openai-whisper (локально)
  3. Backend     — POST /api/voice/transcript (interpret_stub)
  4. LLM-фоллбак — Ollama qwen2.5:3b (при outcome=fallback_to_text)
  5. TTS         — wyoming-piper (TCP :10200)

Зависимости:
  pip install openai-whisper sounddevice soundfile numpy requests wyoming
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import tempfile
import time
from pathlib import Path

import numpy as np
import requests
import sounddevice as sd
import soundfile as sf
import whisper
from wyoming.audio import AudioChunk, AudioStop
from wyoming.client import AsyncTcpClient
from wyoming.tts import Synthesize
from wyoming.wake import Detection

# ---------------------------------------------------------------------------
# Конфиг
# ---------------------------------------------------------------------------

BACKEND_URL       = "http://192.168.0.101:8000"
OLLAMA_URL        = "http://192.168.0.101:11434"
OLLAMA_MODEL      = "qwen2.5:3b"

WAKEWORD_HOST     = "localhost"
WAKEWORD_PORT     = 10400

PIPER_HOST        = "localhost"
PIPER_PORT        = 10200

MIC_DEVICE        = 0
SAMPLE_RATE       = 16000
RECORD_SECS       = 5
SILENCE_THRESHOLD = 0.008
WHISPER_MODEL     = "small"

# ---------------------------------------------------------------------------
# Логгер
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("voice_loop")

# ---------------------------------------------------------------------------
# LLM system-промпт
# English instructions + Russian synonyms = best accuracy for qwen2.5:3b
# ---------------------------------------------------------------------------

_LLM_SYSTEM = """\
You are a smart home controller. Reply ONLY with valid JSON, no explanations, no markdown.

Available intents:
  turn_on_device  -> entities: {room, device_type, target_entity_id}
  turn_off_device -> entities: {room, device_type, target_entity_id}
  activate_scene  -> entities: {scene}
  get_room_status -> entities: {room}

Devices (Russian synonyms -> entity_id):
  торшер, половой светник -> light.living_room_floor_lamp (room: living_room)
  основной свет гостиная, потолочный свет гостиная -> light.living_room_main (room: living_room)
  основной свет кухня -> light.kitchen_main (room: kitchen)
  подсветка кухня -> light.kitchen_accent (room: kitchen)
  основной свет спальня -> light.bedroom_main (room: bedroom)
  прикроватный, ночной свет -> light.bedroom_bedside (room: bedroom)
  шторы гостиная -> cover.living_room_curtains (room: living_room)
  шторы спальня -> cover.bedroom_curtains (room: bedroom)
  чайник -> switch.kitchen_kettle (room: kitchen)
  обогреватель -> switch.bedroom_heater (room: bedroom)

Scenes: good_morning, evening, movie, away
Rooms: kitchen, living_room, bedroom

Examples:
  "включи торшер" -> {"intent":"turn_on_device","entities":{"room":"living_room","device_type":"light","target_entity_id":"light.living_room_floor_lamp"}}
  "выключи чайник" -> {"intent":"turn_off_device","entities":{"room":"kitchen","device_type":"kettle","target_entity_id":"switch.kitchen_kettle"}}
  "включи свет на кухне" -> {"intent":"turn_on_device","entities":{"room":"kitchen","device_type":"light","target_entity_id":"light.kitchen_main"}}
  "доброе утро" -> {"intent":"activate_scene","entities":{"scene":"good_morning"}}
  "что в спальне" -> {"intent":"get_room_status","entities":{"room":"bedroom"}}

If not a smart home command: {"intent": null, "reply": "<short answer in Russian>"}
"""

# ---------------------------------------------------------------------------
# Сборка озвучиваемого текста из backend-ответа
# ---------------------------------------------------------------------------

_DEVICE_RU: dict[str, str] = {
    "light.kitchen_main":          "основной свет на кухне",
    "light.kitchen_accent":        "подсветка на кухне",
    "light.living_room_main":       "основной свет в гостиной",
    "light.living_room_floor_lamp": "торшер в гостиной",
    "light.bedroom_main":           "основной свет в спальне",
    "light.bedroom_bedside":        "прикроватный свет",
    "cover.living_room_curtains":   "шторы в гостиной",
    "cover.bedroom_curtains":       "шторы в спальне",
    "switch.kitchen_kettle":        "чайник",
    "switch.bedroom_heater":        "обогреватель",
}

_SCENE_RU: dict[str, str] = {
    "good_morning": "доброе утро",
    "evening":      "вечер",
    "movie":        "кино",
    "away":         "выход из дома",
}

_ROOM_RU: dict[str, str] = {
    "kitchen":     "кухне",
    "living_room": "гостиной",
    "bedroom":     "спальне",
}


def _spoken_from_backend(resp: dict) -> str:
    outcome = resp.get("outcome", "")
    if outcome == "executed":
        ex = resp.get("execute") or {}
        if ex.get("spoken_response"):
            return str(ex["spoken_response"])
        interp = resp.get("interpret") or {}
        intent = interp.get("canonical_intent", "")
        entities = interp.get("entities") or {}
        if intent == "activate_scene":
            scene = _SCENE_RU.get(entities.get("scene", ""), entities.get("scene", ""))
            return f"Режим {scene} включён."
        if intent in ("turn_on_device", "turn_off_device"):
            action = "включено" if intent == "turn_on_device" else "выключено"
            eid = entities.get("target_entity_id", "")
            device = _DEVICE_RU.get(eid, eid)
            return f"{device.capitalize()} {action}."
        if intent == "get_room_status":
            room = _ROOM_RU.get(entities.get("room", ""), entities.get("room", ""))
            summary = ex.get("result") or ex.get("summary") or "данные получены"
            return f"Статус {room}: {summary}"
        return "Готово."
    return "Не понял команду."


# ---------------------------------------------------------------------------
# Слой 1 — Wake-word
# ---------------------------------------------------------------------------

#async def _wait_wakeword() -> None:
#    log.info("Жду вейквord (скажите 'ассистент')...")
#    async with AsyncTcpClient(WAKEWORD_HOST, WAKEWORD_PORT) as client:
#        async for event in client:
#            if Detection.is_type(event.type):
#                det = Detection.from_event(event)
#                log.info("Вейквord: %s (score=%.3f)", det.name, det.score or 0.0)
#                return
#

# ---------------------------------------------------------------------------
# Слой 2 — STT (Whisper)
# ---------------------------------------------------------------------------

def _record(seconds: int = RECORD_SECS) -> np.ndarray:
    log.info("Запись %d с...", seconds)
    audio = sd.rec(
        int(seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        device=MIC_DEVICE,
    )
    sd.wait()
    return audio.flatten()


def _is_silence(audio: np.ndarray) -> bool:
    mean = float(np.abs(audio).mean())
    log.debug("audio mean_abs=%.5f", mean)
    return mean < SILENCE_THRESHOLD


def _transcribe(model: whisper.Whisper, audio: np.ndarray) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, audio, SAMPLE_RATE)
        result = model.transcribe(f.name, language="ru", fp16=False)
        Path(f.name).unlink(missing_ok=True)
    return result["text"].strip()


# ---------------------------------------------------------------------------
# Слой 3 — Backend (interpret_stub)
# ---------------------------------------------------------------------------

def _call_backend(text: str) -> dict:
    resp = requests.post(
        f"{BACKEND_URL}/api/voice/transcript",
        json={"transcript": text},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Слой 4 — LLM-фоллбак (Ollama)
# ---------------------------------------------------------------------------

def _llm_interpret(text: str) -> dict | None:
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "stream": False,
                "messages": [
                    {"role": "system", "content": _LLM_SYSTEM},
                    {"role": "user",   "content": text},
                ],
            },
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["message"]["content"].strip()
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if not m:
            log.warning("LLM вернул не-JSON: %s", content[:120])
            return None
        return json.loads(m.group())
    except Exception as exc:
        log.warning("LLM ошибка: %s", exc)
        return None


def _execute_via_backend(intent: str, entities: dict, utterance: str) -> dict:
    resp = requests.post(
        f"{BACKEND_URL}/api/intents/execute",
        json={
            "intent":   intent,
            "entities": entities,
            "utterance": utterance,
            "source":   "voice",
            "confidence": 0.85,
            "requires_clarification": False,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _handle_llm_fallback(text: str) -> str:
    log.info("LLM фоллбак: отправляю %r", text)
    parsed = _llm_interpret(text)
    if parsed is None:
        return "Не удалось распознать команду."

    intent = parsed.get("intent")
    if not intent:
        return str(parsed.get("reply", "Не понял команду."))

    entities = parsed.get("entities") or {}
    try:
        ex = _execute_via_backend(intent, entities, text)
        log.info("LLM execute status: %s", ex.get("status"))
        if ex.get("spoken_response"):
            return str(ex["spoken_response"])
        return "Готово." if ex.get("status") == "success" else "Произошла ошибка выполнения."
    except Exception as exc:
        log.warning("execute ошибка: %s", exc)
        return "Не удалось выполнить команду."


# ---------------------------------------------------------------------------
# Слой 5 — TTS (Piper)
# ---------------------------------------------------------------------------

async def _speak_async(text: str) -> None:
    log.info("TTS: %r", text)
    try:
        async with AsyncTcpClient(PIPER_HOST, PIPER_PORT) as client:
            await client.write_event(Synthesize(text=text).event())
            audio_bytes = bytearray()
            async for event in client:
                if AudioChunk.is_type(event.type):
                    audio_bytes += AudioChunk.from_event(event).audio
                elif AudioStop.is_type(event.type):
                    break
        if audio_bytes:
            arr = np.frombuffer(bytes(audio_bytes), dtype=np.int16).astype(np.float32) / 32768.0
            sd.play(arr, samplerate=22050, device=MIC_DEVICE)
            sd.wait()
    except Exception as exc:
        log.warning("TTS ошибка (вывод в консоль): %s", exc)
        print(f"[Ответ] {text}")


def _speak(text: str) -> None:
    asyncio.run(_speak_async(text))


# ---------------------------------------------------------------------------
# Основной цикл
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("Загружаю Whisper %s...", WHISPER_MODEL)
    model = whisper.load_model(WHISPER_MODEL)
    log.info("Модель загружена. Цикл запущен.")

    while True:
        try:
            asyncio.run(_wait_wakeword())
            _speak("Слушаю.")

            audio = _record(RECORD_SECS)
            if _is_silence(audio):
                log.info("Тишина, пропускаю.")
                continue
            text = _transcribe(model, audio)
            if not text:
                log.info("Пустой транскрипт.")
                continue
            log.info("Транскрипт: %r", text)

            resp = _call_backend(text)
            outcome = resp.get("outcome", "")
            log.info("Backend outcome: %s", outcome)

            if outcome == "executed":
                spoken = _spoken_from_backend(resp)
            elif outcome == "fallback_to_text":
                spoken = _handle_llm_fallback(text)
            else:
                spoken = "Голосовой мост недоступен."

            _speak(spoken)

        except KeyboardInterrupt:
            log.info("Остановлено.")
            break
        except Exception as exc:
            log.error("Ошибка цикла: %s", exc, exc_info=True)
            time.sleep(2)


if __name__ == "__main__":
    main()
