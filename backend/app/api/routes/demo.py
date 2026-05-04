from datetime import datetime, timezone

from fastapi import APIRouter
from starlette.requests import Request

from app.api.deps import AppStateDep
from app.models.demo import (
    BaselineStrategy,
    DemoCatalogEntry,
    DemoReplayRequest,
    DemoReplayResponse,
    DemoResetResponse,
    DemoSetModeRequest,
    DemoSetModeResponse,
    DemoStatusResponse,
)
from app.services.baseline_reset import apply_demo_baseline
from app.services.demo_scenario_runner import replay_catalog, run_demo_replay

router = APIRouter(prefix="/api/demo", tags=["demo"])

_RESET_CONTRACT = (
    "POST /api/demo/reset: clears in-memory event log and clarification sessions, "
    "then applies MVP baseline to HA (mock shortcut or best-effort service sequence). "
    "Not a transactional rollback."
)

_MODE_SEMANTICS: dict[str, str] = {
    "static": (
        "Статический режим демо: метка для оператора — перед сценарием выполняйте reset; "
        "replay использует только фиксированный каталог шагов без пользовательского DSL."
    ),
    "live": (
        "Live: обычное выполнение против настроенного Home Assistant; успех сервисов best-effort."
    ),
    "simulator": (
        "Simulator: режим по умолчанию; mock HA в тестах или реальный HA из окружения."
    ),
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@router.get("/status", response_model=DemoStatusResponse)
def demo_status(ctx: AppStateDep) -> DemoStatusResponse:
    catalog = [DemoCatalogEntry.model_validate(row) for row in replay_catalog()]
    mode = ctx.demo_mode
    return DemoStatusResponse(
        mode=mode,
        mode_semantics=_MODE_SEMANTICS.get(mode, _MODE_SEMANTICS["simulator"]),
        last_reset_at=ctx.demo_last_reset_at,
        last_reset_ok=ctx.demo_last_reset_ok,
        last_reset_baseline_strategy=ctx.demo_last_reset_baseline_strategy,
        last_replay_at=ctx.demo_last_replay_at,
        last_replay_summary=ctx.demo_last_replay_summary,
        replay_catalog=catalog,
        reset_contract=_RESET_CONTRACT,
    )


@router.post("/reset", response_model=DemoResetResponse)
def demo_reset(ctx: AppStateDep) -> DemoResetResponse:
    strategy: BaselineStrategy = (
        "mock_reset_to_baseline" if hasattr(ctx.ha_client, "reset_to_baseline") else "ha_service_sequence"
    )
    if strategy == "mock_reset_to_baseline":
        baseline_semantics = (
            "Mock HA: одна операция reset_to_baseline к снимку baseline_ha_states — "
            "детерминировано в CI, без последовательности call_service."
        )
    else:
        baseline_semantics = (
            "Live-like HA: последовательность call_service по шаблону MVP baseline "
            "(см. mvp_house_baseline). Не атомарно: при ошибке в середине возможно частичное применение; "
            "отката «как было» нет."
        )

    try:
        apply_demo_baseline(ctx.ha_client, ctx.ha_write)
    except Exception as e:  # noqa: BLE001 — boundary: surface HA/baseline failures honestly
        at = _iso_now()
        ctx.demo_last_reset_at = at
        ctx.demo_last_reset_ok = False
        ctx.demo_last_reset_baseline_strategy = strategy
        ctx.event_log.append(
            "demo_reset_failed",
            f"Baseline apply failed: {e!s}",
            {"baseline_strategy": strategy, "error": str(e)},
        )
        return DemoResetResponse(
            ok=False,
            message=f"Baseline apply failed (event log not cleared): {e!s}",
            event_log_cleared=False,
            clarification_sessions_cleared=False,
            baseline_strategy=strategy,
            baseline_semantics=baseline_semantics,
            reset_at=at,
        )

    ctx.event_log.clear()
    ctx.clarification_store.clear()
    ctx.event_log.append("demo_reset", "MVP baseline restored via Home Assistant", {})
    at = _iso_now()
    ctx.demo_last_reset_at = at
    ctx.demo_last_reset_ok = True
    ctx.demo_last_reset_baseline_strategy = strategy
    return DemoResetResponse(
        ok=True,
        message="House baseline restored via Home Assistant services (or mock equivalent).",
        event_log_cleared=True,
        clarification_sessions_cleared=True,
        baseline_strategy=strategy,
        baseline_semantics=baseline_semantics,
        reset_at=at,
    )


@router.post("/replay", response_model=DemoReplayResponse)
async def demo_replay(request: Request, ctx: AppStateDep) -> DemoReplayResponse:
    """Accepts optional JSON body; empty body defaults to catalog default scenario."""
    raw = await request.body()
    if raw.strip():
        body = DemoReplayRequest.model_validate_json(raw)
    else:
        body = DemoReplayRequest()
    sid = body.scenario_id or "lights_kitchen_cycle"
    return run_demo_replay(ctx, sid)


@router.post("/set-mode", response_model=DemoSetModeResponse)
def demo_set_mode(body: DemoSetModeRequest, ctx: AppStateDep) -> DemoSetModeResponse:
    ctx.demo_mode = body.mode
    semantics = _MODE_SEMANTICS.get(body.mode, _MODE_SEMANTICS["simulator"])
    ctx.event_log.append("demo_set_mode", f"mode={body.mode}", {"mode": body.mode})
    return DemoSetModeResponse(ok=True, mode=body.mode, semantics=semantics)
