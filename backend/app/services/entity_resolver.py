"""Resolve P4a execution targets from normalized entities (P5: explicit light disambiguation)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.intents.constants import P4A_SCENE_KEYS


class EntityResolutionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class ResolvedDeviceAction:
    kind: Literal["turn_on", "turn_off"]
    entity_id: str


@dataclass(frozen=True)
class ResolvedSceneAction:
    scene_entity_id: str


# MVP lights per room (order stable for clarification options).
ROOM_LIGHT_ENTITIES: dict[str, tuple[str, ...]] = {
    "living_room": ("light.living_room_main", "light.living_room_floor_lamp"),
    "kitchen": ("light.kitchen_main", "light.kitchen_accent"),
    "bedroom": ("light.bedroom_main", "light.bedroom_bedside"),
}

# Explicit non-light device map for minimal deterministic MVP expansion.
ROOM_DEVICE_ENTITY: dict[tuple[str, str], str] = {
    ("living_room", "curtains"): "cover.living_room_curtains",
    ("bedroom", "curtains"): "cover.bedroom_curtains",
    ("kitchen", "kettle"): "switch.kitchen_kettle",
    ("bedroom", "heater"): "switch.bedroom_heater",
}

# Compact Russian labels for clarification / matching (narrow MVP set).
LIGHT_CLARIFICATION_LABEL: dict[str, str] = {
    "light.living_room_main": "Основной свет (гостиная)",
    "light.living_room_floor_lamp": "Торшер (гостиная)",
    "light.kitchen_main": "Основной свет (кухня)",
    "light.kitchen_accent": "Подсветка (кухня)",
    "light.bedroom_main": "Основной свет (спальня)",
    "light.bedroom_bedside": "Прикроватный свет (спальня)",
}

# Lowercased tokens accepted as a deterministic follow-up match (unique per entity in MVP).
LIGHT_REPLY_ALIASES: dict[str, frozenset[str]] = {
    "light.living_room_main": frozenset(
        {"light.living_room_main", "основной", "основной свет (гостиная)", "гостиная основной"}
    ),
    "light.living_room_floor_lamp": frozenset({"light.living_room_floor_lamp", "торшер", "floor lamp"}),
    "light.kitchen_main": frozenset({"light.kitchen_main", "основной", "основной свет (кухня)", "кухня основной"}),
    "light.kitchen_accent": frozenset({"light.kitchen_accent", "подсветка", "accent"}),
    "light.bedroom_main": frozenset({"light.bedroom_main", "основной", "основной свет (спальня)"}),
    "light.bedroom_bedside": frozenset({"light.bedroom_bedside", "прикроватный", "прикроватный свет (спальня)"}),
}

# Reply token -> room_id for narrowing when multiple rooms were in the candidate set.
_ROOM_REPLY_TOKENS: dict[str, str] = {
    "living_room": "living_room",
    "гостиная": "living_room",
    "kitchen": "kitchen",
    "кухня": "kitchen",
    "bedroom": "bedroom",
    "спальня": "bedroom",
}


def resolve_for_intent(intent: str, entities: dict[str, Any]) -> ResolvedDeviceAction | ResolvedSceneAction:
    if intent in ("turn_on_device", "turn_off_device"):
        return _resolve_device(intent, entities)
    if intent == "activate_scene":
        return _resolve_scene(entities)
    raise EntityResolutionError("unsupported_intent", f"Intent is not supported for execution: {intent}")


def list_light_entity_ids_for_room(room: str) -> tuple[str, ...]:
    """Return ordered light entity_ids for a supported room, or raise if room unknown."""
    lights = ROOM_LIGHT_ENTITIES.get(room)
    if lights is None:
        raise EntityResolutionError("unsupported_target", f"Unknown or unsupported room for lights: {room!r}.")
    return lights


def list_all_mvp_light_entity_ids() -> tuple[str, ...]:
    """Deterministic cross-room ordering for room-less light ambiguity."""
    return tuple(
        eid for room in ("living_room", "kitchen", "bedroom") for eid in ROOM_LIGHT_ENTITIES[room]
    )


def infer_room_for_light_entity(entity_id: str) -> str | None:
    for rid, lids in ROOM_LIGHT_ENTITIES.items():
        if entity_id in lids:
            return rid
    return None


def narrow_room_from_reply(reply: str) -> str | None:
    """Map a follow-up token to room_id, or None if not a known room token."""
    key = reply.strip().lower()
    return _ROOM_REPLY_TOKENS.get(key)


def _resolve_device(intent: str, entities: dict[str, Any]) -> ResolvedDeviceAction:
    room = entities.get("room")
    device_type = entities.get("device_type")
    if not isinstance(room, str) or not isinstance(device_type, str):
        raise EntityResolutionError(
            "unsupported_target",
            "Device commands require string entities.room and entities.device_type.",
        )
    target = entities.get("target_entity_id")
    if device_type == "light":
        lights = list_light_entity_ids_for_room(room)
        if isinstance(target, str):
            if target not in lights:
                raise EntityResolutionError(
                    "unsupported_target",
                    f"entities.target_entity_id {target!r} is not a known light for room {room!r}.",
                )
            chosen = target
        elif len(lights) == 1:
            chosen = lights[0]
        else:
            raise EntityResolutionError(
                "ambiguous_light_target",
                "Several lights in this room; provide entities.target_entity_id or run the clarification flow.",
            )
    else:
        mapped = ROOM_DEVICE_ENTITY.get((room, device_type))
        if mapped is None:
            raise EntityResolutionError(
                "unsupported_target",
                f"P4a does not support device_type {device_type!r} in room {room!r}.",
            )
        if isinstance(target, str) and target != mapped:
            raise EntityResolutionError(
                "unsupported_target",
                f"entities.target_entity_id {target!r} does not match canonical target {mapped!r}.",
            )
        chosen = mapped
    kind: Literal["turn_on", "turn_off"] = "turn_on" if intent == "turn_on_device" else "turn_off"
    return ResolvedDeviceAction(kind=kind, entity_id=chosen)


def _resolve_scene(entities: dict[str, Any]) -> ResolvedSceneAction:
    key = entities.get("scene")
    if not isinstance(key, str):
        raise EntityResolutionError("unsupported_target", "Scene activation requires entities.scene as a string key.")
    if key not in P4A_SCENE_KEYS:
        raise EntityResolutionError("unsupported_target", f"Unknown scene key for P4a: {key!r}.")
    return ResolvedSceneAction(scene_entity_id=f"scene.{key}")
