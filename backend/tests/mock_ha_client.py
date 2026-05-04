import copy
from collections.abc import Callable
from typing import Any

from app.integrations.mvp_house_baseline import SCENE_MOCK_EFFECTS, baseline_ha_states


class MockHomeAssistantClient:
    """Test double: HA reads + stateful service calls for P4a execution tests."""

    def __init__(
        self,
        states: list[dict[str, Any]] | None = None,
        *,
        get_states_hook: Callable[[], list[dict[str, Any]]] | None = None,
    ) -> None:
        self._states = copy.deepcopy(baseline_ha_states() if states is None else states)
        self._get_states_hook = get_states_hook
        self.service_calls: list[tuple[str, str, dict[str, Any]]] = []

    def get_states(self) -> list[dict[str, Any]]:
        if self._get_states_hook is not None:
            return copy.deepcopy(self._get_states_hook())
        return copy.deepcopy(self._states)

    def reset_to_baseline(self) -> None:
        self._states = copy.deepcopy(baseline_ha_states())
        self.service_calls.clear()

    def call_service(
        self,
        domain: str,
        service: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        p = dict(payload or {})
        self.service_calls.append((domain, service, p))

        if domain == "scene" and service == "turn_on":
            eid = p.get("entity_id")
            if isinstance(eid, str) and eid in SCENE_MOCK_EFFECTS:
                for target_id, st in SCENE_MOCK_EFFECTS[eid].items():
                    self._set_state(target_id, st)
            return

        entity_id = p.get("entity_id")
        if isinstance(entity_id, list) and entity_id:
            entity_id = entity_id[0]
        if not isinstance(entity_id, str):
            return

        if domain == "climate" and service == "set_hvac_mode":
            mode = p.get("hvac_mode")
            if isinstance(mode, str):
                self._set_state(entity_id, mode)
            return

        if domain == "light":
            if service == "turn_on":
                self._set_state(entity_id, "on")
            elif service == "turn_off":
                self._set_state(entity_id, "off")
            return

        if domain == "switch":
            if service == "turn_on":
                self._set_state(entity_id, "on")
            elif service == "turn_off":
                self._set_state(entity_id, "off")
            return

        if domain == "cover":
            if service == "open_cover":
                self._set_state(entity_id, "open")
            elif service == "close_cover":
                self._set_state(entity_id, "closed")
            return

    def _set_state(self, entity_id: str, state: str) -> None:
        for row in self._states:
            if row.get("entity_id") == entity_id:
                row["state"] = state
                return

    def close(self) -> None:
        pass
