"""P9 optional HA Assist companion: transcript bridge reuses interpret + execute (narrow subset)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import AppStateDep
from app.intents.constants import P4B_STATUS_INTENTS
from app.models.intents import IntentExecuteRequest
from app.models.voice import (
    VoiceProcessResponse,
    VoiceStatusResponse,
    VoiceTranscriptRequest,
    voice_process_bridge_disabled,
    voice_process_executed,
    voice_process_fallback,
)
from app.services.interpret_stub import interpret_text
from app.services.voice_bridge import voice_subset_policy_reason

router = APIRouter(prefix="/api/voice", tags=["voice"])


_SUPPORTED_PHRASES_RU: list[str] = [
    "включи свет на кухне; включи основной свет на кухне → включить light.kitchen_main",
    "выключи свет на кухне → выключить light.kitchen_main",
    "включи режим кино; режим кино → сцена movie",
    "статус кухни; что на кухне → get_room_status (кухня)",
]

_UNSUPPORTED_BULLETS: list[str] = [
    "уточнение interpret (например missing_room) — только текст",
    "неоднозначность света на execute (clarification_required) — продолжение только текстом /api/intents/clarify",
    "compound_action и произвольный NL",
    "get_device_status / get_sensor_status через транскрипт (нет фраз в заглушке interpret)",
]


@router.get("/status", response_model=VoiceStatusResponse)
def voice_status(ctx: AppStateDep) -> VoiceStatusResponse:
    enabled = ctx.voice_bridge_enabled
    return VoiceStatusResponse(
        bridge_enabled=enabled,
        transcript_endpoint_available=enabled,
        ha_assist_local_path=(
            "HA Assist: ru/custom_sentences → intent_script.yaml — сервисы выполняются в HA; "
            "это отдельный локальный путь без записи в журнал событий бэкенда."
        ),
        transcript_bridge_path=(
            "POST /api/voice/transcript: interpret_stub → при узком allowlist — тот же "
            "POST /api/intents/execute (или status) с source=voice."
        ),
        supported_transcript_phrases_ru=list(_SUPPORTED_PHRASES_RU),
        intentionally_unsupported_via_transcript=list(_UNSUPPORTED_BULLETS),
        clarification_policy_ru=(
            "Голосовой транскрипт не ведёт сессии уточнения: при clarification_required "
            "ответ честно предлагает перейти на текст."
        ),
    )


@router.post("/transcript", response_model=VoiceProcessResponse)
def voice_transcript(body: VoiceTranscriptRequest, ctx: AppStateDep) -> VoiceProcessResponse:
    raw = body.transcript.strip()
    if not raw:
        return voice_process_fallback(
            transcript=body.transcript,
            message_ru="Пустой транскрипт.",
            policy_reason="empty_transcript",
            interpret=None,
            execute=None,
        )

    if not ctx.voice_bridge_enabled:
        ctx.event_log.append(
            "voice_transcript",
            "Voice bridge disabled",
            {"transcript": raw, "outcome": "bridge_disabled"},
        )
        return voice_process_bridge_disabled(raw)

    interp = interpret_text(raw)
    if interp.status == "clarification_required":
        ctx.event_log.append(
            "voice_transcript",
            "Voice transcript requires interpret clarification — fallback",
            {"transcript": raw, "interpret_status": interp.status},
        )
        return voice_process_fallback(
            transcript=raw,
            message_ru=(
                "Эта фраза требует уточнения на этапе interpret. Голосовой транскрипт-мост её не выполняет — "
                "введите команду в текстовой консоли или используйте POST /api/intents/interpret."
            ),
            policy_reason="interpret_clarification_not_supported_via_voice",
            interpret=interp,
            execute=None,
        )
    if interp.status == "unsupported" or not interp.canonical_intent:
        ctx.event_log.append(
            "voice_transcript",
            "Unsupported transcript for stub interpret",
            {"transcript": raw, "interpret_status": interp.status},
        )
        return voice_process_fallback(
            transcript=raw,
            message_ru="Фраза не распознана заглушкой interpret. Используйте текстовую консоль или расширьте сценарий вручную.",
            policy_reason="interpret_unsupported",
            interpret=interp,
            execute=None,
        )

    policy = voice_subset_policy_reason(interp)
    if policy is not None:
        ctx.event_log.append(
            "voice_transcript",
            "Transcript rejected by voice subset policy",
            {"transcript": raw, "policy_reason": policy},
        )
        return voice_process_fallback(
            transcript=raw,
            message_ru="Фраза вне узкого голосового подмножества для автозапуска execute. Используйте текстовый путь.",
            policy_reason=policy,
            interpret=interp,
            execute=None,
        )

    req = IntentExecuteRequest(
        intent=interp.canonical_intent,
        source="voice",
        utterance=raw,
        entities=dict(interp.entities),
        confidence=1.0,
        requires_clarification=False,
        meta={"language": "ru", "voice_bridge": True},
    )

    if req.intent in P4B_STATUS_INTENTS:
        ex = ctx.status.query(req)
    else:
        ex = ctx.execution.execute(req)

    if ex.status == "clarification_required":
        ctx.event_log.append(
            "voice_transcript",
            "Execute returned clarification — voice path stops (no session continuation)",
            {"transcript": raw, "intent": req.intent},
        )
        return voice_process_fallback(
            transcript=raw,
            message_ru=(
                "Команда требует уточнения на execute (например несколько светильников). "
                "Голосовой мост не продолжает сессию — используйте текст и POST /api/intents/clarify."
            ),
            policy_reason="execute_clarification_not_supported_via_voice",
            interpret=interp,
            execute=ex,
        )

    ok_or_err = "успех" if ex.status == "success" else "ошибка выполнения"
    ctx.event_log.append(
        "voice_transcript",
        f"Voice transcript executed ({ok_or_err})",
        {"transcript": raw, "intent": req.intent, "execute_status": ex.status},
    )
    msg = (
        "Команда выполнена через голосовой транскрипт-мост (тот же execute, что и у текста)."
        if ex.status == "success"
        else "Выполнение через транскрипт-мост завершилось ошибкой; детали в execute."
    )
    return voice_process_executed(transcript=raw, message_ru=msg, interpret=interp, execute=ex)
