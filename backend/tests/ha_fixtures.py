"""Sample HA /api/states payloads for tests (no live HA)."""

from __future__ import annotations

from typing import Any

from app.integrations.mvp_house_baseline import baseline_ha_states


def states_with_helpers() -> list[dict[str, Any]]:
    """Includes internal P2 helpers that must not appear in the public house model."""
    helpers: list[dict[str, Any]] = [
        {"entity_id": "input_boolean.kitchen_main_internal", "state": "on", "attributes": {}},
        {"entity_id": "input_boolean.living_room_motion_sim", "state": "off", "attributes": {}},
    ]
    return baseline_ha_states() + helpers
