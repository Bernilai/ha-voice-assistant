"""Restore MVP demo house to baseline via HA service calls (or mock reset hook)."""

from __future__ import annotations

from typing import Any, Protocol

from app.integrations.ha_write_adapter import HAWriteAdapter
from app.integrations.mvp_house_baseline import baseline_ha_states


class _HAClientLike(Protocol):
    def call_service(self, domain: str, service: str, payload: dict[str, Any] | None = None) -> None:
        ...


def apply_demo_baseline(ha_client: _HAClientLike, ha_write: HAWriteAdapter) -> None:
    """Idempotent baseline: lights/switches off, covers open, climate heat (best-effort).

    Branching: ``reset_to_baseline`` (e.g. tests' MockHomeAssistantClient) is a deliberate shortcut
    so pytest does not depend on replaying the full service sequence. Production / live-like clients
    take the loop below: best-effort and non-atomic (no rollback if a mid-sequence call fails).
    """
    if hasattr(ha_client, "reset_to_baseline"):
        ha_client.reset_to_baseline()  # type: ignore[attr-defined]
        return

    for row in baseline_ha_states():
        entity_id = row["entity_id"]
        if not isinstance(entity_id, str):
            continue
        domain = entity_id.split(".", 1)[0]
        desired = row.get("state")
        if not isinstance(desired, str):
            continue
        if domain in ("sensor", "binary_sensor"):
            continue
        if domain == "climate":
            ha_client.call_service(
                "climate",
                "set_hvac_mode",
                {"entity_id": entity_id, "hvac_mode": desired},
            )
            continue
        if domain == "cover":
            if desired in ("open", "opening"):
                ha_write.turn_on(entity_id)
            elif desired in ("closed", "closing"):
                ha_write.turn_off(entity_id)
            continue
        if domain in ("light", "switch"):
            if desired == "on":
                ha_write.turn_on(entity_id)
            else:
                ha_write.turn_off(entity_id)
            continue
