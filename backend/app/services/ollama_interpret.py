"""Ollama-based NLU fallback: called when interpret_stub returns 'unsupported'."""

from __future__ import annotations

import json
import logging
import os
import re

import httpx

from app.intents.constants import P4A_SCENE_KEYS
from app.models.intents import IntentInterpretResponse
from app.services.status_resolver import P4B_SENSOR_STATUS_PAIRS

logger = logging.getLogger(__name__)

_DEFAULT_OLLAMA_TIMEOUT_SEC = 15.0


def _parse_ollama_timeout_seconds(raw: str | None) -> float:
    """Parse OLLAMA_TIMEOUT; invalid or empty values log a warning and fall back to default."""
    if raw is None:
        return _DEFAULT_OLLAMA_TIMEOUT_SEC
    s = str(raw).strip()
    if not s:
        return _DEFAULT_OLLAMA_TIMEOUT_SEC
    try:
        return float(s)
    except ValueError:
        logger.warning(
            "Invalid OLLAMA_TIMEOUT=%r (expected a number); using %.1f seconds",
            raw,
            _DEFAULT_OLLAMA_TIMEOUT_SEC,
        )
        return _DEFAULT_OLLAMA_TIMEOUT_SEC


_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
_OLLAMA_TIMEOUT = _parse_ollama_timeout_seconds(os.environ.get("OLLAMA_TIMEOUT"))

# Known entity_ids for validation
_KNOWN_ENTITIES: frozenset[str] = frozenset({
    "light.kitchen_main",
    "light.kitchen_accent",
    "light.bedroom_main",
    "light.bedroom_bedside",
    "light.living_room_main",
    "light.living_room_floor_lamp",
    "switch.kitchen_kettle",
    "switch.bedroom_heater",
    "cover.living_room_curtains",
    "cover.bedroom_curtains",
    "climate.bedroom_heater",
})

_VALID_INTENTS: frozenset[str] = frozenset({
    "turn_on_device",
    "turn_off_device",
    "activate_scene",
    "get_room_status",
    "get_sensor_status",
})

_VALID_ROOMS: frozenset[str] = frozenset({"kitchen", "bedroom", "living_room"})

_VALID_DEVICE_TYPES: frozenset[str] = frozenset({"light", "kettle", "heater", "curtains"})

_SYSTEM_PROMPT = """\
You are a smart home NLU assistant. The user speaks Russian.
Extract intent and entities from the user's command.

Respond ONLY with valid JSON in this exact format:
{
  "intent": "<intent>",
  "entities": { <key>: <value>, ... }
}

Available intents and required entities:
- turn_on_device: {"room": "kitchen|bedroom|living_room", "device_type": "light|kettle|heater|curtains", "target_entity_id": "<entity_id>"}
- turn_off_device: same as turn_on_device
- activate_scene: {"scene": "movie|good_morning|evening|away"}
- get_room_status: {"room": "kitchen|bedroom|living_room"}
- get_sensor_status: {"room", "sensor_kind"} must be a supported pair: kitchen+temperature|window, bedroom+temperature|humidity, living_room+temperature|motion (same matrix as P4b status resolver)

Known entity_ids:
- light.kitchen_main, light.kitchen_accent
- light.bedroom_main, light.bedroom_bedside
- light.living_room_main, light.living_room_floor_lamp
- switch.kitchen_kettle, switch.bedroom_heater
- cover.living_room_curtains, cover.bedroom_curtains

Scene keywords in Russian:
- movie: режим кино, кинорежим, кино
- good_morning: доброе утро, утренний режим
- evening: вечерний режим, вечер
- away: я ухожу, режим отсутствия

If you cannot determine the intent with confidence, respond:
{"intent": null, "entities": {}}

Do not add any explanation. Only JSON.
"""


def _call_ollama(text: str) -> dict | None:
    payload = {
        "model": _OLLAMA_MODEL,
        "prompt": f"User command: {text}",
        "system": _SYSTEM_PROMPT,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.0, "num_predict": 256},
    }
    try:
        resp = httpx.post(
            f"{_OLLAMA_URL}/api/generate",
            json=payload,
            timeout=_OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "")
        # Strip markdown code fences if model wraps output (language tag is often mixed case)
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw.strip())
        raw = re.sub(r"```$", "", raw.strip())
        return json.loads(raw)
    except httpx.TimeoutException:
        logger.warning("Ollama NLU timeout for: %s", text)
    except httpx.HTTPStatusError as e:
        logger.warning("Ollama NLU HTTP error: %s", e)
    except httpx.RequestError as e:
        logger.warning("Ollama NLU request error: %s", e)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Ollama NLU bad JSON: %s", e)
    return None


def _validate(parsed: dict) -> IntentInterpretResponse | None:
    """Validate Ollama output against known intents/entities. Returns None if invalid."""
    intent = parsed.get("intent")
    raw_entities = parsed.get("entities", {})
    if raw_entities is None:
        raw_entities = {}
    if not isinstance(raw_entities, dict):
        return None
    entities: dict = raw_entities

    if not intent or intent not in _VALID_INTENTS:
        return None

    if intent in ("turn_on_device", "turn_off_device"):
        tid = entities.get("target_entity_id")
        if not isinstance(tid, str) or tid not in _KNOWN_ENTITIES:
            logger.warning("Ollama NLU: unknown entity_id '%s'", tid)
            return None
        room = entities.get("room")
        if room not in _VALID_ROOMS:
            return None
        dt = entities.get("device_type")
        if dt not in _VALID_DEVICE_TYPES:
            return None

    if intent == "activate_scene":
        if entities.get("scene") not in P4A_SCENE_KEYS:
            return None

    if intent == "get_room_status":
        if entities.get("room") not in _VALID_ROOMS:
            return None

    if intent == "get_sensor_status":
        room = entities.get("room")
        kind = entities.get("sensor_kind")
        if not isinstance(room, str) or not isinstance(kind, str):
            return None
        if (room, kind) not in P4B_SENSOR_STATUS_PAIRS:
            return None

    return IntentInterpretResponse(
        raw_text="",
        normalized_text="",
        canonical_intent=intent,
        entities=entities,
        status="success",
    )


def ollama_interpret(raw: str) -> IntentInterpretResponse:
    """
    Call Ollama to interpret raw text.
    Returns IntentInterpretResponse with status='success' on valid result,
    or status='unsupported' if Ollama fails/returns invalid data.
    """
    parsed = _call_ollama(raw)
    if parsed is None:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=raw,
            canonical_intent=None, entities={}, status="unsupported",
        )

    result = _validate(parsed)
    if result is None:
        logger.info("Ollama NLU: validation failed for '%s', parsed=%s", raw, parsed)
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=raw,
            canonical_intent=None, entities={}, status="unsupported",
        )

    result = result.model_copy(update={"raw_text": raw, "normalized_text": raw})
    logger.info("Ollama NLU: '%s' → intent=%s entities=%s", raw, result.canonical_intent, result.entities)
    return result
