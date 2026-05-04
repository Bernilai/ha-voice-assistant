"""Demo control models (P7: reset semantics, set-mode, scripted replay catalog)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


BaselineStrategy = Literal["mock_reset_to_baseline", "ha_service_sequence"]


class DemoResetResponse(BaseModel):
    ok: bool = True
    message: str = "House baseline restored via Home Assistant services."
    event_log_cleared: bool = True
    clarification_sessions_cleared: bool = True
    baseline_strategy: BaselineStrategy = "ha_service_sequence"
    baseline_semantics: str = Field(
        ...,
        description="Human-readable honesty: mock shortcut vs best-effort HA sequence.",
    )
    reset_at: str = Field(..., description="ISO-8601 UTC timestamp when reset completed.")


class DemoReplayStepResult(BaseModel):
    index: int
    intent: str
    status: str
    error_code: str | None = None


class DemoReplayRequest(BaseModel):
    """Optional body for POST /api/demo/replay."""

    scenario_id: str | None = Field(
        default="lights_kitchen_cycle",
        description="One of the fixed catalog ids from GET /api/demo/status.",
    )


class DemoReplayResponse(BaseModel):
    ok: bool = Field(..., description="True only if every step returned status success.")
    scenario_id: str
    steps_total: int
    steps_run: int
    stopped_early: bool = Field(
        ...,
        description="True if a step returned non-success and following steps were skipped.",
    )
    step_results: list[DemoReplayStepResult] = Field(default_factory=list)
    detail: str
    completed_at: str | None = Field(default=None, description="ISO-8601 UTC when replay finished or stopped.")


class DemoSetModeRequest(BaseModel):
    mode: Literal["static", "live", "simulator"]


class DemoSetModeResponse(BaseModel):
    ok: bool = True
    mode: str
    semantics: str = Field(
        ...,
        description="What this mode means in this MVP (metadata; not a second house truth).",
    )


class DemoCatalogEntry(BaseModel):
    id: str
    title: str
    steps: int
    deterministic: bool = True
    notes: str = ""


class DemoStatusResponse(BaseModel):
    mode: str
    mode_semantics: str
    last_reset_at: str | None = None
    last_reset_ok: bool | None = None
    last_reset_baseline_strategy: BaselineStrategy | None = None
    last_replay_at: str | None = None
    last_replay_summary: dict[str, Any] | None = None
    replay_catalog: list[DemoCatalogEntry] = Field(default_factory=list)
    reset_contract: str = Field(
        default="",
        description="Short fixed summary of reset side effects for operators.",
    )
