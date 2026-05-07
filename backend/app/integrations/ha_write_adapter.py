"""Narrow write seam for P4a (no intent/scenario logic here)."""

from __future__ import annotations

from app.integrations.ha_client import HomeAssistantClient


class HAWriteAdapter:
    def __init__(self, client: HomeAssistantClient) -> None:
        self._client = client

    def turn_on(self, entity_id: str) -> None:
        domain, _ = entity_id.split(".", 1)
        service = "open_cover" if domain == "cover" else "turn_on"
        self._client.call_service(domain, service, {"entity_id": entity_id})

    def turn_off(self, entity_id: str) -> None:
        domain, _ = entity_id.split(".", 1)
        service = "close_cover" if domain == "cover" else "turn_off"
        self._client.call_service(domain, service, {"entity_id": entity_id})

    def activate_scene(self, scene_entity_id: str) -> None:
        self._client.call_service("scene", "turn_on", {"entity_id": scene_entity_id})

    def set_temperature(self, entity_id: str, temperature: int) -> None:
        """Set target temperature on a climate entity (heater) or switch+attr (kettle)."""
        domain, _ = entity_id.split(".", 1)
        if domain == "climate":
            self._client.call_service(
                "climate", "set_temperature",
                {"entity_id": entity_id, "temperature": temperature},
            )
        else:
            # For switch-based devices (kettle): turn on and pass target_temp attribute.
            # HA helpers or automations pick up target_temp from the service call data.
            self._client.call_service(
                domain, "turn_on",
                {"entity_id": entity_id, "target_temp": temperature},
            )
