"""Live-like baseline reset branch: no reset_to_baseline shortcut, deterministic service sequence."""

from __future__ import annotations

from typing import Any

from app.integrations.ha_write_adapter import HAWriteAdapter
from app.services.baseline_reset import apply_demo_baseline


class _RecordingHAClient:
    """Fake HA client: only call_service; intentionally no reset_to_baseline."""

    def __init__(self) -> None:
        self.service_calls: list[tuple[str, str, dict[str, Any]]] = []

    def call_service(
        self,
        domain: str,
        service: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.service_calls.append((domain, service, dict(payload or {})))


def test_apply_demo_baseline_live_branch_service_call_sequence() -> None:
    """Guards the non-shortcut path: order and payloads stay tied to mvp_house_baseline rows."""
    client = _RecordingHAClient()
    apply_demo_baseline(client, HAWriteAdapter(client))

    expected: list[tuple[str, str, dict[str, Any]]] = [
        ("light", "turn_off", {"entity_id": "light.living_room_main"}),
        ("light", "turn_off", {"entity_id": "light.living_room_floor_lamp"}),
        ("cover", "open_cover", {"entity_id": "cover.living_room_curtains"}),
        ("light", "turn_off", {"entity_id": "light.kitchen_main"}),
        ("light", "turn_off", {"entity_id": "light.kitchen_accent"}),
        ("switch", "turn_off", {"entity_id": "switch.kitchen_kettle"}),
        ("light", "turn_off", {"entity_id": "light.bedroom_main"}),
        ("light", "turn_off", {"entity_id": "light.bedroom_bedside"}),
        ("cover", "open_cover", {"entity_id": "cover.bedroom_curtains"}),
        ("switch", "turn_off", {"entity_id": "switch.bedroom_heater"}),
        (
            "climate",
            "set_hvac_mode",
            {"entity_id": "climate.bedroom_heater", "hvac_mode": "heat"},
        ),
    ]
    assert client.service_calls == expected
