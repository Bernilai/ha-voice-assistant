"""P9 narrow transcript bridge: same interpret stub + execute/status as text, explicit allowlist."""

from __future__ import annotations

from app.intents.constants import P4A_SCENE_KEYS
from app.models.intents import IntentInterpretResponse

_VOICE_ROOMS: frozenset[str] = frozenset({"living_room", "kitchen", "bedroom"})

# All device_types allowed for on/off via voice
_VOICE_DEVICE_TYPES: frozenset[str] = frozenset({
    "light",
    "curtains",
    "kettle",
    "heater",
})


def voice_subset_policy_reason(interp: IntentInterpretResponse) -> str | None:
    """
    Return a stable machine reason if this interpret result must not auto-execute via voice transcript,
    or None if allowed for the narrow voice subset.
    """
    if interp.status != "success" or not interp.canonical_intent:
        return "interpret_not_executable"
    intent = interp.canonical_intent
    ent = interp.entities

    if intent in ("turn_on_device", "turn_off_device"):
        if ent.get("device_type") not in _VOICE_DEVICE_TYPES:
            return "voice_device_type_not_in_subset"
        tid = ent.get("target_entity_id")
        if not isinstance(tid, str) or not tid.strip():
            return "voice_requires_target_entity_id"
        return None

    if intent == "activate_scene":
        sk = ent.get("scene")
        if sk not in P4A_SCENE_KEYS:
            return "voice_scene_not_in_catalog"
        return None

    if intent == "get_room_status":
        room = ent.get("room")
        if room not in _VOICE_ROOMS:
            return "voice_room_not_in_subset"
        return None

    if intent == "get_sensor_status":
        room = ent.get("room")
        if room not in _VOICE_ROOMS:
            return "voice_room_not_in_subset"
        return None

    return "voice_intent_not_in_subset"
