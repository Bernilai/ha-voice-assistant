"""Deterministic text → stub interpretation (no NLP). Ollama NLU fallback when enabled."""

from __future__ import annotations

import os
import re

from app.models.intents import IntentInterpretResponse

_OLLAMA_NLU_ENABLED = os.environ.get("OLLAMA_NLU_ENABLED", "false").lower() == "true"


def _norm(text: str) -> str:
    t = text.strip().lower()
    t = t.replace("е", "е")
    t = re.sub(r"[.!?,;:]+$", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


# ---------------------------------------------------------------------------
# Temperature helpers
# ---------------------------------------------------------------------------

_RE_TEMP = re.compile(r"(\d+)\s*(?:градус(?:ов|а|)?|°c|°)", re.IGNORECASE)


def _extract_temp(text: str) -> int | None:
    m = _RE_TEMP.search(text)
    return int(m.group(1)) if m else None


def _kettle_temp(text: str) -> int | None:
    """Return validated kettle temperature (40-100) or None if out of range."""
    t = _extract_temp(text)
    if t is None:
        return None
    return t if 40 <= t <= 100 else None


def _heater_temp(text: str) -> int | None:
    """Return validated heater temperature (10-35) or None if out of range."""
    t = _extract_temp(text)
    if t is None:
        return None
    return t if 10 <= t <= 35 else None


# ---------------------------------------------------------------------------
# Phrase tables  (imperative + infinitive + we-form + common STT variants)
# ---------------------------------------------------------------------------

_ON_KITCHEN_LIGHT = {
    "включи свет на кухне",
    "включите свет на кухне",
    "включить свет на кухне",
    "включим свет на кухне",
    "включи основной свет на кухне",
    "включить основной свет на кухне",
    "свет на кухне включи",
    "свет на кухне включить",
}

_OFF_KITCHEN_LIGHT = {
    "выключи свет на кухне",
    "выключите свет на кухне",
    "выключить свет на кухне",
    "выключим свет на кухне",
    "свет на кухне выключи",
    "свет на кухне выключить",
}

_ON_KITCHEN_ACCENT = {
    "включи подсветку на кухне",
    "включите подсветку на кухне",
    "включить подсветку на кухне",
    "включим подсветку на кухне",
    "подсветка на кухне включи",
    "подсветка кухни включи",
    "включи кухонную подсветку",
    "включить кухонную подсветку",
}

_OFF_KITCHEN_ACCENT = {
    "выключи подсветку на кухне",
    "выключите подсветку на кухне",
    "выключить подсветку на кухне",
    "выключим подсветку на кухне",
    "подсветка на кухне выключи",
    "подсветка кухни выключи",
    "выключи кухонную подсветку",
    "выключить кухонную подсветку",
}

_ON_LIVING_LIGHT = {
    "включи свет в гостиной",
    "включите свет в гостиной",
    "включить свет в гостиной",
    "включим свет в гостиной",
    "свет в гостиной включи",
    "свет в гостиной включить",
}

_OFF_LIVING_LIGHT = {
    "выключи свет в гостиной",
    "выключите свет в гостиной",
    "выключить свет в гостиной",
    "выключим свет в гостиной",
    "свет в гостиной выключи",
    "свет в гостиной выключить",
}

_ON_LIVING_FLOOR_LAMP = {
    "включи торшер в гостиной",
    "включите торшер в гостиной",
    "включить торшер в гостиной",
    "включим торшер в гостиной",
    "торшер в гостиной включи",
    "торшер включи",
    "включи торшер",
    "включить торшер",
}

_OFF_LIVING_FLOOR_LAMP = {
    "выключи торшер в гостиной",
    "выключите торшер в гостиной",
    "выключить торшер в гостиной",
    "выключим торшер в гостиной",
    "торшер в гостиной выключи",
    "торшер выключи",
    "выключи торшер",
    "выключить торшер",
}

_ON_BEDROOM_LIGHT = {
    "включи свет в спальне",
    "включите свет в спальне",
    "включить свет в спальне",
    "включим свет в спальне",
    "свет в спальне включи",
    "свет в спальне включить",
}

_OFF_BEDROOM_LIGHT = {
    "выключи свет в спальне",
    "выключите свет в спальне",
    "выключить свет в спальне",
    "выключим свет в спальне",
    "свет в спальне выключи",
    "свет в спальне выключить",
}

_ON_BEDROOM_BEDSIDE = {
    "включи прикроватный свет",
    "включить прикроватный свет",
    "включите прикроватный свет",
    "включим прикроватный свет",
    "включи ночник",
    "включить ночник",
    "ночник включи",
    "прикроватный свет включи",
}

_OFF_BEDROOM_BEDSIDE = {
    "выключи прикроватный свет",
    "выключить прикроватный свет",
    "выключите прикроватный свет",
    "выключим прикроватный свет",
    "выключи ночник",
    "выключить ночник",
    "ночник выключи",
    "прикроватный свет выключи",
}

_OPEN_LIVING_CURTAINS = {
    "открой шторы в гостиной",
    "откройте шторы в гостиной",
    "открыть шторы в гостиной",
    "откроем шторы в гостиной",
    "раздвинь шторы в гостиной",
    "раздвинуть шторы в гостиной",
}

_CLOSE_LIVING_CURTAINS = {
    "закрой шторы в гостиной",
    "закройте шторы в гостиной",
    "закрыть шторы в гостиной",
    "закроем шторы в гостиной",
    "задвинь шторы в гостиной",
    "задвинуть шторы в гостиной",
}

_OPEN_BEDROOM_CURTAINS = {
    "открой шторы в спальне",
    "откройте шторы в спальне",
    "открыть шторы в спальне",
    "откроем шторы в спальне",
    "раздвинь шторы в спальне",
    "раздвинуть шторы в спальне",
}

_CLOSE_BEDROOM_CURTAINS = {
    "закрой шторы в спальне",
    "закройте шторы в спальне",
    "закрыть шторы в спальне",
    "закроем шторы в спальне",
    "задвинь шторы в спальне",
    "задвинуть шторы в спальне",
}

_ON_KETTLE = {
    "включи чайник",
    "включите чайник",
    "включить чайник",
    "включим чайник",
    "чайник включи",
    "чайник включить",
    "поставь чайник",
    "поставить чайник",
}

_OFF_KETTLE = {
    "выключи чайник",
    "выключите чайник",
    "выключить чайник",
    "выключим чайник",
    "чайник выключи",
    "чайник выключить",
}

# Kettle temperature patterns (with explicit degree mention)
_RE_KETTLE_TEMP = re.compile(
    r"(?:вскипяти|подогрей|нагрей|включи чайник до|поставь чайник до|чайник до|нагреть до|подогреть до)"
    r".*?(\d+)\s*(?:градус(?:ов|а|)?|°c|°)",
    re.IGNORECASE,
)

_ON_HEATER = {
    "включи обогреватель в спальне",
    "включите обогреватель в спальне",
    "включить обогреватель в спальне",
    "включим обогреватель в спальне",
    "обогреватель в спальне включи",
    "обогреватель в спальне включить",
    "включи обогреватель",
    "включить обогреватель",
}

_OFF_HEATER = {
    "выключи обогреватель в спальне",
    "выключите обогреватель в спальне",
    "выключить обогреватель в спальне",
    "выключим обогреватель в спальне",
    "обогреватель в спальне выключи",
    "обогреватель в спальне выключить",
    "выключи обогреватель",
    "выключить обогреватель",
}

# Heater temperature patterns
_RE_HEATER_TEMP = re.compile(
    r"(?:установи|поставь|выставь|установить|задай|задать)\s+(?:температуру\s+)?(?:обогревателя?\s+)?(?:на\s+)?"
    r"(\d+)\s*(?:градус(?:ов|а|)?|°c|°)"
    r"|(?:обогреватель|обогрей).*?(\d+)\s*(?:градус(?:ов|а|)?|°c|°)",
    re.IGNORECASE,
)

_TEMP_BEDROOM = {
    "какая температура в спальне",
    "температура в спальне",
    "какая температура спальни",
    "температура спальни",
    "сколько градусов в спальне",
}

_TEMP_KITCHEN = {
    "какая температура на кухне",
    "температура на кухне",
    "какая температура кухни",
    "температура кухни",
    "сколько градусов на кухне",
}

_TEMP_LIVING = {
    "какая температура в гостиной",
    "температура в гостиной",
    "какая температура гостиной",
    "температура гостиной",
    "сколько градусов в гостиной",
}

_HUMIDITY_BEDROOM = {
    "влажность в спальне",
    "какая влажность в спальне",
    "влажность спальни",
    "сколько влажность в спальне",
    "покажи влажность в спальне",
}

_STATUS_WINDOW_KITCHEN = {
    "окно на кухне",
    "открыто ли окно на кухне",
    "статус окна на кухне",
    "окно кухни",
}

_STATUS_MOTION_LIVING = {
    "движение в гостиной",
    "есть ли движение в гостиной",
    "статус движения в гостиной",
    "датчик движения в гостиной",
}

# Scenes -----------------------------------------------------------------------

_SCENE_MOVIE = {
    "включи режим кино",
    "включить режим кино",
    "включим режим кино",
    "режим кино",
    "кинорежим",
    "поставь режим кино",
    "поставьте режим кино",
    "киносеанс",
}

_SCENE_GOOD_MORNING = {
    "доброе утро",
    "включи режим доброе утро",
    "включить режим доброе утро",
    "включи сцену доброе утро",
    "режим доброе утро",
    "утренний режим",
    "включи утренний режим",
    "включить утренний режим",
}

_SCENE_EVENING = {
    "вечерний режим",
    "включи вечерний режим",
    "включить вечерний режим",
    "включи сцену вечер",
    "режим вечер",
    "сцена вечер",
}

_SCENE_AWAY = {
    "я ухожу",
    "я ушел",
    "я ушла",
    "включи режим я ушел",
    "включить режим я ушел",
    "режим ухожу",
    "режим отсутствия",
    "включи режим отсутствия",
    "включить режим отсутствия",
    "выходной режим",
}

# Room status ------------------------------------------------------------------

_STATUS_KITCHEN = {
    "статус кухни",
    "что на кухне",
    "что включено на кухне",
    "покажи статус кухни",
    "статус кухня",
}

_STATUS_LIVING = {
    "статус гостиной",
    "что в гостиной",
    "что включено в гостиной",
    "покажи статус гостиной",
    "статус гостиная",
}

_STATUS_BEDROOM = {
    "статус спальни",
    "что в спальне",
    "что включено в спальне",
    "покажи статус спальни",
    "статус спальня",
}

# Clarifications (missing room) ------------------------------------------------

_CLARIFY_LIGHT_OFF = {
    "выключи свет",
    "выключить свет",
    "выключите свет",
    "выключим свет",
}

_CLARIFY_LIGHT_ON = {
    "включи свет",
    "включить свет",
    "включите свет",
    "включим свет",
}


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def interpret_text(raw: str) -> IntentInterpretResponse:
    """Phrase table lookup first; Ollama NLU fallback if enabled and phrase unknown."""
    n = _norm(raw)

    if n in _ON_KITCHEN_LIGHT:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="turn_on_device",
            entities={"room": "kitchen", "device_type": "light", "target_entity_id": "light.kitchen_main"},
            status="success",
        )

    if n in _OFF_KITCHEN_LIGHT:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="turn_off_device",
            entities={"room": "kitchen", "device_type": "light", "target_entity_id": "light.kitchen_main"},
            status="success",
        )

    if n in _ON_KITCHEN_ACCENT:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="turn_on_device",
            entities={"room": "kitchen", "device_type": "light", "target_entity_id": "light.kitchen_accent"},
            status="success",
        )

    if n in _OFF_KITCHEN_ACCENT:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="turn_off_device",
            entities={"room": "kitchen", "device_type": "light", "target_entity_id": "light.kitchen_accent"},
            status="success",
        )

    if n in _ON_LIVING_LIGHT:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="turn_on_device",
            entities={"room": "living_room", "device_type": "light", "target_entity_id": "light.living_room_main"},
            status="success",
        )

    if n in _OFF_LIVING_LIGHT:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="turn_off_device",
            entities={"room": "living_room", "device_type": "light", "target_entity_id": "light.living_room_main"},
            status="success",
        )

    if n in _ON_LIVING_FLOOR_LAMP:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="turn_on_device",
            entities={"room": "living_room", "device_type": "light", "target_entity_id": "light.living_room_floor_lamp"},
            status="success",
        )

    if n in _OFF_LIVING_FLOOR_LAMP:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="turn_off_device",
            entities={"room": "living_room", "device_type": "light", "target_entity_id": "light.living_room_floor_lamp"},
            status="success",
        )

    if n in _ON_BEDROOM_LIGHT:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="turn_on_device",
            entities={"room": "bedroom", "device_type": "light", "target_entity_id": "light.bedroom_main"},
            status="success",
        )

    if n in _OFF_BEDROOM_LIGHT:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="turn_off_device",
            entities={"room": "bedroom", "device_type": "light", "target_entity_id": "light.bedroom_main"},
            status="success",
        )

    if n in _ON_BEDROOM_BEDSIDE:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="turn_on_device",
            entities={"room": "bedroom", "device_type": "light", "target_entity_id": "light.bedroom_bedside"},
            status="success",
        )

    if n in _OFF_BEDROOM_BEDSIDE:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="turn_off_device",
            entities={"room": "bedroom", "device_type": "light", "target_entity_id": "light.bedroom_bedside"},
            status="success",
        )

    if n in _OPEN_LIVING_CURTAINS:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="turn_on_device",
            entities={"room": "living_room", "device_type": "curtains", "target_entity_id": "cover.living_room_curtains"},
            status="success",
        )

    if n in _CLOSE_LIVING_CURTAINS:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="turn_off_device",
            entities={"room": "living_room", "device_type": "curtains", "target_entity_id": "cover.living_room_curtains"},
            status="success",
        )

    if n in _OPEN_BEDROOM_CURTAINS:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="turn_on_device",
            entities={"room": "bedroom", "device_type": "curtains", "target_entity_id": "cover.bedroom_curtains"},
            status="success",
        )

    if n in _CLOSE_BEDROOM_CURTAINS:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="turn_off_device",
            entities={"room": "bedroom", "device_type": "curtains", "target_entity_id": "cover.bedroom_curtains"},
            status="success",
        )

    if n in _ON_KETTLE:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="turn_on_device",
            entities={"room": "kitchen", "device_type": "kettle", "target_entity_id": "switch.kitchen_kettle"},
            status="success",
        )

    if n in _OFF_KETTLE:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="turn_off_device",
            entities={"room": "kitchen", "device_type": "kettle", "target_entity_id": "switch.kitchen_kettle"},
            status="success",
        )

    # Kettle with temperature: "вскипяти до 80 градусов", "нагрей чайник до 60°", etc.
    m_kettle = _RE_KETTLE_TEMP.search(n)
    if m_kettle:
        t = int(m_kettle.group(1))
        if 40 <= t <= 100:
            return IntentInterpretResponse(
                raw_text=raw, normalized_text=n,
                canonical_intent="set_temperature",
                entities={
                    "device_type": "kettle",
                    "target_entity_id": "switch.kitchen_kettle",
                    "target_temp": t,
                },
                status="success",
            )
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent=None, entities={}, status="unsupported",
            clarification={"reason": "temp_out_of_range",
                           "prompt": "Для чайника допустимая температура от 40 до 100 градусов."},
        )

    # Kettle: explicit keyword but no temperature → 100°C default
    if re.search(r"(?:вскипяти|вскипятить|подогрей|нагрей чайник|нагреть чайник)", n):
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="set_temperature",
            entities={
                "device_type": "kettle",
                "target_entity_id": "switch.kitchen_kettle",
                "target_temp": 100,
            },
            status="success",
        )

    if n in _ON_HEATER:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="turn_on_device",
            entities={"room": "bedroom", "device_type": "heater", "target_entity_id": "switch.bedroom_heater"},
            status="success",
        )

    if n in _OFF_HEATER:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="turn_off_device",
            entities={"room": "bedroom", "device_type": "heater", "target_entity_id": "switch.bedroom_heater"},
            status="success",
        )

    # Heater with temperature
    m_heater = _RE_HEATER_TEMP.search(n)
    if m_heater:
        t = int(m_heater.group(1) or m_heater.group(2))
        if 10 <= t <= 35:
            return IntentInterpretResponse(
                raw_text=raw, normalized_text=n,
                canonical_intent="set_temperature",
                entities={
                    "device_type": "heater",
                    "target_entity_id": "climate.bedroom_heater",
                    "target_temp": t,
                },
                status="success",
            )
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent=None, entities={}, status="unsupported",
            clarification={"reason": "temp_out_of_range",
                           "prompt": "Для обогревателя допустимая температура от 10 до 35 градусов."},
        )

    if n in _TEMP_BEDROOM:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="get_sensor_status",
            entities={"room": "bedroom", "sensor_kind": "temperature"},
            status="success",
        )

    if n in _TEMP_KITCHEN:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="get_sensor_status",
            entities={"room": "kitchen", "sensor_kind": "temperature"},
            status="success",
        )

    if n in _TEMP_LIVING:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="get_sensor_status",
            entities={"room": "living_room", "sensor_kind": "temperature"},
            status="success",
        )

    if n in _HUMIDITY_BEDROOM:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="get_sensor_status",
            entities={"room": "bedroom", "sensor_kind": "humidity"},
            status="success",
        )

    if n in _STATUS_WINDOW_KITCHEN:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="get_device_status",
            entities={"room": "kitchen", "device_type": "window", "target_entity_id": "binary_sensor.kitchen_window"},
            status="success",
        )

    if n in _STATUS_MOTION_LIVING:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="get_device_status",
            entities={"room": "living_room", "device_type": "motion", "target_entity_id": "binary_sensor.living_room_motion"},
            status="success",
        )

    if n in _SCENE_MOVIE:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="activate_scene",
            entities={"scene": "movie"},
            status="success",
        )

    if n in _SCENE_GOOD_MORNING:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="activate_scene",
            entities={"scene": "good_morning"},
            status="success",
        )

    if n in _SCENE_EVENING:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="activate_scene",
            entities={"scene": "evening"},
            status="success",
        )

    if n in _SCENE_AWAY:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="activate_scene",
            entities={"scene": "away"},
            status="success",
        )

    if n in _STATUS_KITCHEN:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="get_room_status",
            entities={"room": "kitchen"},
            status="success",
        )

    if n in _STATUS_LIVING:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="get_room_status",
            entities={"room": "living_room"},
            status="success",
        )

    if n in _STATUS_BEDROOM:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent="get_room_status",
            entities={"room": "bedroom"},
            status="success",
        )

    if n in _CLARIFY_LIGHT_OFF:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
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

    if n in _CLARIFY_LIGHT_ON:
        return IntentInterpretResponse(
            raw_text=raw, normalized_text=n,
            canonical_intent=None,
            entities={},
            status="clarification_required",
            clarification={
                "reason": "missing_room",
                "prompt": "В какой комнате включить свет?",
                "options": [
                    {"label": "Гостиная", "room": "living_room"},
                    {"label": "Кухня", "room": "kitchen"},
                    {"label": "Спальня", "room": "bedroom"},
                ],
            },
        )

    # --- Ollama NLU fallback ---
    if _OLLAMA_NLU_ENABLED:
        from app.services.ollama_interpret import ollama_interpret  # lazy import
        return ollama_interpret(raw)

    return IntentInterpretResponse(
        raw_text=raw,
        normalized_text=n,
        canonical_intent=None,
        entities={},
        status="unsupported",
        clarification=None,
    )
