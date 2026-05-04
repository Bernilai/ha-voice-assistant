"""Write seam delegates to HA client (mocked)."""

from __future__ import annotations

from app.integrations.ha_write_adapter import HAWriteAdapter

from tests.mock_ha_client import MockHomeAssistantClient


def test_write_adapter_turn_on_cover_and_scene() -> None:
    mock = MockHomeAssistantClient()
    adapter = HAWriteAdapter(mock)
    adapter.turn_on("light.kitchen_main")
    adapter.turn_off("light.kitchen_main")
    adapter.turn_on("cover.living_room_curtains")
    adapter.turn_off("cover.living_room_curtains")
    adapter.activate_scene("scene.movie")
    assert mock.service_calls == [
        ("light", "turn_on", {"entity_id": "light.kitchen_main"}),
        ("light", "turn_off", {"entity_id": "light.kitchen_main"}),
        ("cover", "open_cover", {"entity_id": "cover.living_room_curtains"}),
        ("cover", "close_cover", {"entity_id": "cover.living_room_curtains"}),
        ("scene", "turn_on", {"entity_id": "scene.movie"}),
    ]
