"""P7: fixed catalog of deterministic demo replay steps (backend-owned, no DSL)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Final

from app.intents.constants import P4B_STATUS_INTENTS
from app.models.demo import DemoReplayResponse, DemoReplayStepResult
from app.models.intents import IntentExecuteRequest
from app.state import AppState

# Each entry: minimal execute payload; runner fills source/meta.
_SCENARIO_STEPS: Final[dict[str, list[dict[str, Any]]]] = {
    "lights_kitchen_cycle": [
        {
            "intent": "turn_off_device",
            "utterance": "demo-replay: kitchen off",
            "entities": {
                "room": "kitchen",
                "device_type": "light",
                "target_entity_id": "light.kitchen_main",
            },
        },
        {
            "intent": "turn_on_device",
            "utterance": "demo-replay: kitchen on",
            "entities": {
                "room": "kitchen",
                "device_type": "light",
                "target_entity_id": "light.kitchen_main",
            },
        },
        {
            "intent": "turn_off_device",
            "utterance": "demo-replay: kitchen off",
            "entities": {
                "room": "kitchen",
                "device_type": "light",
                "target_entity_id": "light.kitchen_main",
            },
        },
    ],
    "room_status_kitchen": [
        {
            "intent": "get_room_status",
            "utterance": "demo-replay: status kitchen",
            "entities": {"room": "kitchen"},
        },
    ],
    "scene_movie": [
        {
            "intent": "activate_scene",
            "utterance": "demo-replay: scene movie",
            "entities": {"scene": "movie"},
        },
    ],
    "compound_kitchen_bedroom_on": [
        {
            "intent": "compound_action",
            "utterance": "demo-replay: compound two rooms",
            "entities": {
                "steps": [
                    {
                        "intent": "turn_on_device",
                        "entities": {
                            "room": "kitchen",
                            "device_type": "light",
                            "target_entity_id": "light.kitchen_main",
                        },
                    },
                    {
                        "intent": "turn_on_device",
                        "entities": {
                            "room": "bedroom",
                            "device_type": "light",
                            "target_entity_id": "light.bedroom_main",
                        },
                    },
                ],
            },
        },
    ],
}

_CATALOG_META: Final[list[dict[str, Any]]] = [
    {
        "id": "lights_kitchen_cycle",
        "title": "Цикл света кухни (явные entity_id)",
        "steps": len(_SCENARIO_STEPS["lights_kitchen_cycle"]),
        "deterministic": True,
        "notes": "Только P4a с target_entity_id; без ambiguity.",
    },
    {
        "id": "room_status_kitchen",
        "title": "Статус комнаты «кухня» (P4b read-only)",
        "steps": len(_SCENARIO_STEPS["room_status_kitchen"]),
        "deterministic": True,
        "notes": "Один get_room_status; без записи в HA.",
    },
    {
        "id": "scene_movie",
        "title": "Сцена «кино»",
        "steps": len(_SCENARIO_STEPS["scene_movie"]),
        "deterministic": True,
        "notes": "Один activate_scene; на mock применяются фиксированные эффекты сцены.",
    },
    {
        "id": "compound_kitchen_bedroom_on",
        "title": "Составная команда: кухня + спальня on",
        "steps": len(_SCENARIO_STEPS["compound_kitchen_bedroom_on"]),
        "deterministic": True,
        "notes": "Два шага compound_action с явными target_entity_id.",
    },
]


def replay_catalog() -> list[dict[str, Any]]:
    return list(_CATALOG_META)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_demo_replay(ctx: AppState, scenario_id: str) -> DemoReplayResponse:
    """Run a fixed scenario sequentially; stop on first non-success."""
    steps_raw = _SCENARIO_STEPS.get(scenario_id)
    if not steps_raw:
        return DemoReplayResponse(
            ok=False,
            scenario_id=scenario_id,
            steps_total=0,
            steps_run=0,
            stopped_early=False,
            step_results=[],
            detail=f"Unknown scenario_id {scenario_id!r}. See GET /api/demo/status for catalog.",
            completed_at=None,
        )

    step_results: list[DemoReplayStepResult] = []
    total = len(steps_raw)
    for i, row in enumerate(steps_raw):
        merged = {
            **row,
            "source": "demo_replay",
            "confidence": 1.0,
            "requires_clarification": False,
            "meta": {"language": "ru", "demo_replay": True, "scenario_id": scenario_id, "step_index": i},
        }
        body = IntentExecuteRequest.model_validate(merged)
        if body.intent in P4B_STATUS_INTENTS:
            resp = ctx.status.query(body)
        else:
            resp = ctx.execution.execute(body)
        step_results.append(
            DemoReplayStepResult(
                index=i,
                intent=body.intent,
                status=resp.status,
                error_code=resp.error_code,
            ),
        )
        if resp.status != "success":
            ctx.event_log.append(
                "demo_replay",
                f"Replay {scenario_id!r} stopped at step {i}",
                {
                    "scenario_id": scenario_id,
                    "step_index": i,
                    "status": resp.status,
                    "error_code": resp.error_code,
                },
            )
            completed = _iso_now()
            ctx.demo_last_replay_at = completed
            ctx.demo_last_replay_summary = {
                "scenario_id": scenario_id,
                "ok": False,
                "steps_run": i + 1,
                "steps_total": total,
                "stopped_early": True,
            }
            return DemoReplayResponse(
                ok=False,
                scenario_id=scenario_id,
                steps_total=total,
                steps_run=i + 1,
                stopped_early=True,
                step_results=step_results,
                detail=f"Stopped at step {i} ({body.intent}): status={resp.status}",
                completed_at=completed,
            )

    completed = _iso_now()
    ctx.event_log.append(
        "demo_replay",
        f"Replay {scenario_id!r} completed ({total} steps)",
        {"scenario_id": scenario_id, "steps_total": total},
    )
    ctx.demo_last_replay_at = completed
    ctx.demo_last_replay_summary = {
        "scenario_id": scenario_id,
        "ok": True,
        "steps_run": total,
        "steps_total": total,
        "stopped_early": False,
    }
    return DemoReplayResponse(
        ok=True,
        scenario_id=scenario_id,
        steps_total=total,
        steps_run=total,
        stopped_early=False,
        step_results=step_results,
        detail=f"Scenario {scenario_id!r} finished successfully ({total} steps).",
        completed_at=completed,
    )
