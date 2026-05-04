"""Canonical MVP house baseline rows (aligned with P2 HA templates and tests)."""

from __future__ import annotations

from typing import Any


def baseline_ha_states() -> list[dict[str, Any]]:
    """Minimal realistic rows for all public MVP entities (P2 template ids)."""
    return [
        {
            "entity_id": "light.living_room_main",
            "state": "off",
            "attributes": {"friendly_name": "Гостиная основной свет"},
        },
        {
            "entity_id": "light.living_room_floor_lamp",
            "state": "off",
            "attributes": {"friendly_name": "Гостиная торшер"},
        },
        {
            "entity_id": "cover.living_room_curtains",
            "state": "open",
            "attributes": {"friendly_name": "Гостиная шторы", "device_class": "curtain"},
        },
        {
            "entity_id": "sensor.living_room_temperature",
            "state": "21.5",
            "attributes": {
                "friendly_name": "Гостиная температура",
                "device_class": "temperature",
                "unit_of_measurement": "°C",
            },
        },
        {
            "entity_id": "binary_sensor.living_room_motion",
            "state": "off",
            "attributes": {"friendly_name": "Гостиная движение", "device_class": "motion"},
        },
        {
            "entity_id": "light.kitchen_main",
            "state": "off",
            "attributes": {"friendly_name": "Кухня основной свет"},
        },
        {
            "entity_id": "light.kitchen_accent",
            "state": "off",
            "attributes": {"friendly_name": "Кухня подсветка"},
        },
        {
            "entity_id": "switch.kitchen_kettle",
            "state": "off",
            "attributes": {"friendly_name": "Кухня чайник"},
        },
        {
            "entity_id": "sensor.kitchen_temperature",
            "state": "22.0",
            "attributes": {
                "friendly_name": "Кухня температура",
                "device_class": "temperature",
                "unit_of_measurement": "°C",
            },
        },
        {
            "entity_id": "binary_sensor.kitchen_window",
            "state": "off",
            "attributes": {"friendly_name": "Кухня окно", "device_class": "window"},
        },
        {
            "entity_id": "light.bedroom_main",
            "state": "off",
            "attributes": {"friendly_name": "Спальня основной свет"},
        },
        {
            "entity_id": "light.bedroom_bedside",
            "state": "off",
            "attributes": {"friendly_name": "Спальня прикроватный свет"},
        },
        {
            "entity_id": "cover.bedroom_curtains",
            "state": "open",
            "attributes": {"friendly_name": "Спальня шторы", "device_class": "curtain"},
        },
        {
            "entity_id": "switch.bedroom_heater",
            "state": "off",
            "attributes": {"friendly_name": "Спальня обогреватель"},
        },
        {
            "entity_id": "climate.bedroom_heater",
            "state": "heat",
            "attributes": {"friendly_name": "Bedroom Heater"},
        },
        {
            "entity_id": "sensor.bedroom_temperature",
            "state": "20.0",
            "attributes": {
                "friendly_name": "Спальня температура",
                "device_class": "temperature",
                "unit_of_measurement": "°C",
            },
        },
        {
            "entity_id": "sensor.bedroom_humidity",
            "state": "45",
            "attributes": {
                "friendly_name": "Спальня влажность",
                "device_class": "humidity",
                "unit_of_measurement": "%",
            },
        },
    ]


# scene_entity_id -> {entity_id: desired_state} for mock simulation (subset of ha/scenes.yaml)
SCENE_MOCK_EFFECTS: dict[str, dict[str, str]] = {
    "scene.movie": {
        "light.living_room_main": "off",
        "light.living_room_floor_lamp": "off",
        "light.kitchen_main": "off",
        "light.kitchen_accent": "on",
        "cover.living_room_curtains": "closed",
    },
}
