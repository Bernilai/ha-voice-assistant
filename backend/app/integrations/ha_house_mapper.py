"""
Map Home Assistant /api/states into GET /api/state/house payload.

Only explicitly listed MVP entities appear in the public model (no full HA dump).
Helper / simulation entities (e.g. input_boolean.* internals from P2 templates) are
never referenced here and therefore never exposed.
"""

from __future__ import annotations

from typing import Any

from app.models.house import DeviceState, HouseStatePayload, RoomState, SensorState

# --- Explicit public MVP surface (aligns with ha/packages/* P2 template entity_ids) ---

# Internal HA helpers excluded by design (not listed below), for example:
# - input_boolean.living_room_main_internal, input_boolean.kitchen_main_internal, ...
# - input_boolean.*_sim, input_boolean.*_closed, etc.

_LIVING_ROOM_DEVICES: tuple[str, ...] = (
    "light.living_room_main",
    "light.living_room_floor_lamp",
    "cover.living_room_curtains",
)

_LIVING_ROOM_SENSORS: tuple[str, ...] = (
    "sensor.living_room_temperature",
    "binary_sensor.living_room_motion",
)

_KITCHEN_DEVICES: tuple[str, ...] = (
    "light.kitchen_main",
    "light.kitchen_accent",
    "switch.kitchen_kettle",
)

_KITCHEN_SENSORS: tuple[str, ...] = (
    "sensor.kitchen_temperature",
    "binary_sensor.kitchen_window",
)

_BEDROOM_DEVICES: tuple[str, ...] = (
    "light.bedroom_main",
    "light.bedroom_bedside",
    "cover.bedroom_curtains",
    "switch.bedroom_heater",
    "climate.bedroom_heater",
)

_BEDROOM_SENSORS: tuple[str, ...] = (
    "sensor.bedroom_temperature",
    "sensor.bedroom_humidity",
)

# Default friendly names if HA has not materialized the entity yet.
_DEFAULT_NAMES: dict[str, str] = {
    "light.living_room_main": "Гостиная основной свет",
    "light.living_room_floor_lamp": "Гостиная торшер",
    "cover.living_room_curtains": "Гостиная шторы",
    "sensor.living_room_temperature": "Гостиная температура",
    "binary_sensor.living_room_motion": "Гостиная движение",
    "light.kitchen_main": "Кухня основной свет",
    "light.kitchen_accent": "Кухня подсветка",
    "switch.kitchen_kettle": "Кухня чайник",
    "sensor.kitchen_temperature": "Кухня температура",
    "binary_sensor.kitchen_window": "Кухня окно",
    "light.bedroom_main": "Спальня основной свет",
    "light.bedroom_bedside": "Спальня прикроватный свет",
    "cover.bedroom_curtains": "Спальня шторы",
    "switch.bedroom_heater": "Спальня обогреватель",
    "climate.bedroom_heater": "Bedroom Heater",
    "sensor.bedroom_temperature": "Спальня температура",
    "sensor.bedroom_humidity": "Спальня влажность",
}


def _index_states(states: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in states:
        eid = row.get("entity_id")
        if isinstance(eid, str):
            out[eid] = row
    return out


def _device_from_ha(entity_id: str, row: dict[str, Any] | None) -> DeviceState:
    domain = entity_id.split(".", 1)[0]
    if row is None:
        return DeviceState(
            entity_id=entity_id,
            domain=domain,
            name=_DEFAULT_NAMES.get(entity_id, entity_id),
            state="unavailable",
            device_class=None,
        )
    attrs = row.get("attributes") if isinstance(row.get("attributes"), dict) else {}
    name = attrs.get("friendly_name") or _DEFAULT_NAMES.get(entity_id, entity_id)
    dc = attrs.get("device_class")
    device_class = dc if isinstance(dc, str) else None
    st = row.get("state")
    state = st if isinstance(st, str) else "unknown"
    return DeviceState(
        entity_id=entity_id,
        domain=domain,
        name=str(name),
        state=state,
        device_class=device_class,
    )


_SENSOR_KINDS: dict[str, str] = {
    "sensor.living_room_temperature": "temperature",
    "binary_sensor.living_room_motion": "motion",
    "sensor.kitchen_temperature": "temperature",
    "binary_sensor.kitchen_window": "window",
    "sensor.bedroom_temperature": "temperature",
    "sensor.bedroom_humidity": "humidity",
}


def _sensor_from_ha(entity_id: str, row: dict[str, Any] | None) -> SensorState:
    kind = _SENSOR_KINDS.get(entity_id, "unknown")
    if row is None:
        return SensorState(
            entity_id=entity_id,
            kind=kind,
            name=_DEFAULT_NAMES.get(entity_id, entity_id),
            state="unavailable",
            unit=None,
        )
    attrs = row.get("attributes") if isinstance(row.get("attributes"), dict) else {}
    name = attrs.get("friendly_name") or _DEFAULT_NAMES.get(entity_id, entity_id)
    st = row.get("state")
    state = st if isinstance(st, str) else "unknown"
    unit = attrs.get("unit_of_measurement")
    unit_out = unit if isinstance(unit, str) else None
    return SensorState(
        entity_id=entity_id,
        kind=kind,
        name=str(name),
        state=state,
        unit=unit_out,
    )


def _room(
    room_id: str,
    title: str,
    index: dict[str, dict[str, Any]],
    devices: tuple[str, ...],
    sensors: tuple[str, ...],
) -> RoomState:
    return RoomState(
        room_id=room_id,
        name=title,
        devices=[_device_from_ha(eid, index.get(eid)) for eid in devices],
        sensors=[_sensor_from_ha(eid, index.get(eid)) for eid in sensors],
    )


def build_house_payload_from_ha_states(states: list[dict[str, Any]]) -> HouseStatePayload:
    index = _index_states(states)
    rooms = [
        _room("living_room", "Гостиная", index, _LIVING_ROOM_DEVICES, _LIVING_ROOM_SENSORS),
        _room("kitchen", "Кухня", index, _KITCHEN_DEVICES, _KITCHEN_SENSORS),
        _room("bedroom", "Спальня", index, _BEDROOM_DEVICES, _BEDROOM_SENSORS),
    ]
    return HouseStatePayload(version="p3-ha", rooms=rooms)
