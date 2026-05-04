"""Process-wide services: HA-backed reads and writes; no duplicate in-memory house state."""

from __future__ import annotations

import os
from typing import Any

from app.integrations.ha_client import HomeAssistantClient
from app.integrations.ha_house_mapper import build_house_payload_from_ha_states
from app.integrations.ha_write_adapter import HAWriteAdapter
from app.models.house import HouseStatePayload
from app.services.clarification_service import ClarificationService
from app.services.clarification_store import ClarificationStore
from app.services.compound_service import CompoundService
from app.services.event_log import EventLogService
from app.services.execution_orchestrator import ExecutionOrchestrator
from app.services.scenario_engine import ScenarioEngine
from app.services.status_service import StatusService


def _env_bool(key: str, default: bool = True) -> bool:
    raw = os.environ.get(key)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


class AppState:
    """Holds singleton-like services for one app process."""

    def __init__(
        self,
        *,
        ha_client: Any = None,
    ) -> None:
        self.event_log = EventLogService()
        self.ha_client: Any = ha_client if ha_client is not None else HomeAssistantClient.from_env()
        self.ha_write = HAWriteAdapter(self.ha_client)
        self.clarification_store = ClarificationStore(ttl_seconds=120.0)
        self.scenario = ScenarioEngine(self.ha_write, self.event_log)
        self.clarification_service = ClarificationService(
            self.clarification_store,
            self.event_log,
            self.scenario,
        )
        self.compound_service = CompoundService(self.scenario, self.event_log)
        self.execution = ExecutionOrchestrator(
            self.scenario,
            self.compound_service,
            self.clarification_service,
            self.event_log,
        )
        self.status = StatusService(house_supplier=self.house_payload_from_ha, events=self.event_log)
        # P9: optional transcript bridge; operators may toggle via env without code changes.
        self.voice_bridge_enabled: bool = _env_bool("VOICE_BRIDGE_ENABLED", True)
        self.demo_mode: str = "simulator"
        self.demo_last_reset_at: str | None = None
        self.demo_last_reset_ok: bool | None = None
        self.demo_last_reset_baseline_strategy: str | None = None
        self.demo_last_replay_at: str | None = None
        self.demo_last_replay_summary: dict[str, Any] | None = None

    def rebind_ha_stack(self) -> None:
        """Rebuild HA write adapter and downstream execution services (tests may swap ha_client)."""
        self.ha_write = HAWriteAdapter(self.ha_client)
        self.scenario = ScenarioEngine(self.ha_write, self.event_log)
        self.clarification_service = ClarificationService(
            self.clarification_store,
            self.event_log,
            self.scenario,
        )
        self.compound_service = CompoundService(self.scenario, self.event_log)
        self.execution = ExecutionOrchestrator(
            self.scenario,
            self.compound_service,
            self.clarification_service,
            self.event_log,
        )

    def house_payload_from_ha(self) -> HouseStatePayload:
        raw = self.ha_client.get_states()
        return build_house_payload_from_ha_states(raw)
