"""Resolve P4b read-only status targets from normalized entities (no NL, no ambiguity)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

# MVP rooms aligned with ha_house_mapper / P4a primary lights.
_SUPPORTED_ROOMS: frozenset[str] = frozenset({"living_room", "kitchen", "bedroom"})

_ROOM_PRIMARY_LIGHT: dict[str, str] = {
    "living_room": "light.living_room_main",
    "kitchen": "light.kitchen_main",
    "bedroom": "light.bedroom_main",
}

# (room_id, sensor_kind) -> HA entity_id. Narrow explicit subset for P4b.
_SENSOR_ENTITY: dict[tuple[str, str], str] = {
    ("living_room", "temperature"): "sensor.living_room_temperature",
    ("living_room", "motion"): "binary_sensor.living_room_motion",
    ("kitchen", "temperature"): "sensor.kitchen_temperature",
    ("kitchen", "window"): "binary_sensor.kitchen_window",
    ("bedroom", "temperature"): "sensor.bedroom_temperature",
    ("bedroom", "humidity"): "sensor.bedroom_humidity",
}

# Exposed for NLU / validation layers; keep in sync with _resolve_sensor.
P4B_SENSOR_STATUS_PAIRS: Final[frozenset[tuple[str, str]]] = frozenset(_SENSOR_ENTITY.keys())


class StatusResolutionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class ResolvedRoomStatus:
    room_id: str


@dataclass(frozen=True)
class ResolvedDeviceStatus:
    room_id: str
    device_type: str
    entity_id: str


@dataclass(frozen=True)
class ResolvedSensorStatus:
    room_id: str
    sensor_kind: str
    entity_id: str


def resolve_status_intent(
    intent: str,
    entities: dict[str, Any],
) -> ResolvedRoomStatus | ResolvedDeviceStatus | ResolvedSensorStatus:
    if intent == "get_room_status":
        return _resolve_room(entities)
    if intent == "get_device_status":
        return _resolve_device(entities)
    if intent == "get_sensor_status":
        return _resolve_sensor(entities)
    raise StatusResolutionError("unsupported_intent", f"Not a P4b status intent: {intent!r}.")


def _resolve_room(entities: dict[str, Any]) -> ResolvedRoomStatus:
    room = entities.get("room")
    if not isinstance(room, str):
        raise StatusResolutionError(
            "unsupported_target",
            "get_room_status requires entities.room as a string.",
        )
    if room not in _SUPPORTED_ROOMS:
        raise StatusResolutionError("unsupported_target", f"Unknown or unsupported room: {room!r}.")
    return ResolvedRoomStatus(room_id=room)


def _resolve_device(entities: dict[str, Any]) -> ResolvedDeviceStatus:
    room = entities.get("room")
    device_type = entities.get("device_type")
    if not isinstance(room, str) or not isinstance(device_type, str):
        raise StatusResolutionError(
            "unsupported_target",
            "get_device_status requires string entities.room and entities.device_type.",
        )
    if room not in _SUPPORTED_ROOMS:
        raise StatusResolutionError("unsupported_target", f"Unknown or unsupported room: {room!r}.")
    if device_type != "light":
        raise StatusResolutionError(
            "unsupported_target",
            "P4b get_device_status supports only device_type 'light' (primary room light).",
        )
    entity_id = _ROOM_PRIMARY_LIGHT.get(room)
    if entity_id is None:
        raise StatusResolutionError("unsupported_target", f"No primary light mapped for room {room!r}.")
    return ResolvedDeviceStatus(room_id=room, device_type=device_type, entity_id=entity_id)


def _resolve_sensor(entities: dict[str, Any]) -> ResolvedSensorStatus:
    room = entities.get("room")
    kind = entities.get("sensor_kind")
    if not isinstance(room, str) or not isinstance(kind, str):
        raise StatusResolutionError(
            "unsupported_target",
            "get_sensor_status requires string entities.room and entities.sensor_kind.",
        )
    key = (room, kind)
    entity_id = _SENSOR_ENTITY.get(key)
    if entity_id is None:
        raise StatusResolutionError(
            "unsupported_target",
            f"Unsupported room/sensor_kind pair for P4b: {room!r} / {kind!r}.",
        )
    return ResolvedSensorStatus(room_id=room, sensor_kind=kind, entity_id=entity_id)
