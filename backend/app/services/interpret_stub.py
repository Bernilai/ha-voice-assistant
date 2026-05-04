"""Deterministic text → stub interpretation (no NLP)."""

from __future__ import annotations

import re
from typing import Any

from app.models.intents import IntentInterpretResponse


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def interpret_text(raw: str) -> IntentInterpretResponse:
    """Tiny phrase table + fallbacks; no ML."""
    n = _norm(raw)

    if n in ("включи свет на кухне", "включи основной свет на кухне"):
        return IntentInterpretResponse(
            raw_text=raw,
            normalized_text=n,
            canonical_intent="turn_on_device",
            entities={
                "room": "kitchen",
                "device_type": "light",
                "target_entity_id": "light.kitchen_main",
            },
            status="success",
        )

    if n in ("выключи свет на кухне",):
        return IntentInterpretResponse(
            raw_text=raw,
            normalized_text=n,
            canonical_intent="turn_off_device",
            entities={
                "room": "kitchen",
                "device_type": "light",
                "target_entity_id": "light.kitchen_main",
            },
            status="success",
        )

    if n in ("включи свет в гостиной",):
        return IntentInterpretResponse(
            raw_text=raw,
            normalized_text=n,
            canonical_intent="turn_on_device",
            entities={
                "room": "living_room",
                "device_type": "light",
                "target_entity_id": "light.living_room_main",
            },
            status="success",
        )

    if n in ("выключи свет в гостиной",):
        return IntentInterpretResponse(
            raw_text=raw,
            normalized_text=n,
            canonical_intent="turn_off_device",
            entities={
                "room": "living_room",
                "device_type": "light",
                "target_entity_id": "light.living_room_main",
            },
            status="success",
        )

    if n in ("включи свет в спальне",):
        return IntentInterpretResponse(
            raw_text=raw,
            normalized_text=n,
            canonical_intent="turn_on_device",
            entities={
                "room": "bedroom",
                "device_type": "light",
                "target_entity_id": "light.bedroom_main",
            },
            status="success",
        )

    if n in ("выключи свет в спальне",):
        return IntentInterpretResponse(
            raw_text=raw,
            normalized_text=n,
            canonical_intent="turn_off_device",
            entities={
                "room": "bedroom",
                "device_type": "light",
                "target_entity_id": "light.bedroom_main",
            },
            status="success",
        )

    if n in ("открой шторы в гостиной",):
        return IntentInterpretResponse(
            raw_text=raw,
            normalized_text=n,
            canonical_intent="turn_on_device",
            entities={
                "room": "living_room",
                "device_type": "curtains",
                "target_entity_id": "cover.living_room_curtains",
            },
            status="success",
        )

    if n in ("закрой шторы в гостиной",):
        return IntentInterpretResponse(
            raw_text=raw,
            normalized_text=n,
            canonical_intent="turn_off_device",
            entities={
                "room": "living_room",
                "device_type": "curtains",
                "target_entity_id": "cover.living_room_curtains",
            },
            status="success",
        )

    if n in ("открой шторы в спальне",):
        return IntentInterpretResponse(
            raw_text=raw,
            normalized_text=n,
            canonical_intent="turn_on_device",
            entities={
                "room": "bedroom",
                "device_type": "curtains",
                "target_entity_id": "cover.bedroom_curtains",
            },
            status="success",
        )

    if n in ("закрой шторы в спальне",):
        return IntentInterpretResponse(
            raw_text=raw,
            normalized_text=n,
            canonical_intent="turn_off_device",
            entities={
                "room": "bedroom",
                "device_type": "curtains",
                "target_entity_id": "cover.bedroom_curtains",
            },
            status="success",
        )

    if n in ("включи чайник",):
        return IntentInterpretResponse(
            raw_text=raw,
            normalized_text=n,
            canonical_intent="turn_on_device",
            entities={
                "room": "kitchen",
                "device_type": "kettle",
                "target_entity_id": "switch.kitchen_kettle",
            },
            status="success",
        )

    if n in ("выключи чайник",):
        return IntentInterpretResponse(
            raw_text=raw,
            normalized_text=n,
            canonical_intent="turn_off_device",
            entities={
                "room": "kitchen",
                "device_type": "kettle",
                "target_entity_id": "switch.kitchen_kettle",
            },
            status="success",
        )

    if n in ("включи обогреватель в спальне",):
        return IntentInterpretResponse(
            raw_text=raw,
            normalized_text=n,
            canonical_intent="turn_on_device",
            entities={
                "room": "bedroom",
                "device_type": "heater",
                "target_entity_id": "switch.bedroom_heater",
            },
            status="success",
        )

    if n in ("выключи обогреватель в спальне",):
        return IntentInterpretResponse(
            raw_text=raw,
            normalized_text=n,
            canonical_intent="turn_off_device",
            entities={
                "room": "bedroom",
                "device_type": "heater",
                "target_entity_id": "switch.bedroom_heater",
            },
            status="success",
        )

    if n in ("какая температура в спальне",):
        return IntentInterpretResponse(
            raw_text=raw,
            normalized_text=n,
            canonical_intent="get_sensor_status",
            entities={
                "room": "bedroom",
                "sensor_kind": "temperature",
            },
            status="success",
        )

    if n in ("какая температура на кухне",):
        return IntentInterpretResponse(
            raw_text=raw,
            normalized_text=n,
            canonical_intent="get_sensor_status",
            entities={
                "room": "kitchen",
                "sensor_kind": "temperature",
            },
            status="success",
        )

    if n in ("какая температура в гостиной",):
        return IntentInterpretResponse(
            raw_text=raw,
            normalized_text=n,
            canonical_intent="get_sensor_status",
            entities={
                "room": "living_room",
                "sensor_kind": "temperature",
            },
            status="success",
        )

    if n in ("включи режим кино", "режим кино"):
        return IntentInterpretResponse(
            raw_text=raw,
            normalized_text=n,
            canonical_intent="activate_scene",
            entities={"scene": "movie"},
            status="success",
        )

    if n in ("статус кухни", "что на кухне"):
        return IntentInterpretResponse(
            raw_text=raw,
            normalized_text=n,
            canonical_intent="get_room_status",
            entities={"room": "kitchen"},
            status="success",
        )

    if n in ("выключи свет",):
        return IntentInterpretResponse(
            raw_text=raw,
            normalized_text=n,
            canonical_intent=None,
            entities={},
            status="clarification_required",
            clarification={
                "reason": "missing_room",
                "prompt": "В какой комнате выключить свет?",
                "options": [
                    {"label": "Гостиная", "room": "living_room"},
                    {"label": "Кухня", "room": "kitchen"},
                    {"label": "Спальня", "room": "bedroom"},
                ],
            },
        )

    return IntentInterpretResponse(
        raw_text=raw,
        normalized_text=n,
        canonical_intent=None,
        entities={},
        status="unsupported",
        clarification=None,
    )
