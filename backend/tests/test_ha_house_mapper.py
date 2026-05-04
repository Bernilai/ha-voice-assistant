"""Normalization from HA /api/states rows to public house model."""

from __future__ import annotations

import json

from app.integrations.ha_house_mapper import build_house_payload_from_ha_states
from app.integrations.mvp_house_baseline import baseline_ha_states

from tests.ha_fixtures import states_with_helpers


def test_normalize_baseline_matches_room_ids_and_kitchen_light() -> None:
    payload = build_house_payload_from_ha_states(baseline_ha_states())
    assert payload.version == "p3-ha"
    ids = {r.room_id for r in payload.rooms}
    assert ids == {"living_room", "kitchen", "bedroom"}
    kitchen = next(r for r in payload.rooms if r.room_id == "kitchen")
    main = next(d for d in kitchen.devices if d.entity_id == "light.kitchen_main")
    assert main.state == "off"
    assert main.domain == "light"


def test_helpers_in_ha_payload_not_in_public_json() -> None:
    house = build_house_payload_from_ha_states(states_with_helpers())
    text = json.dumps(house.model_dump())
    assert "input_boolean" not in text


def test_missing_entity_shows_unavailable() -> None:
    partial = [x for x in baseline_ha_states() if x["entity_id"] != "light.kitchen_main"]
    house = build_house_payload_from_ha_states(partial)
    kitchen = next(r for r in house.rooms if r.room_id == "kitchen")
    main = next(d for d in kitchen.devices if d.entity_id == "light.kitchen_main")
    assert main.state == "unavailable"
