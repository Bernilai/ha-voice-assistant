"""P5: two-step compound_action (sequential, explicit validation)."""

from __future__ import annotations

from typing import Any

from app.intents.constants import COMPOUND_ACTION_INTENT, P4A_EXECUTE_INTENTS
from app.models.intents import IntentExecuteRequest, IntentExecuteResponse
from app.services.entity_resolver import EntityResolutionError, resolve_for_intent
from app.services.event_log import EventLogService
from app.services.response_builder import ExecutionResponseBuilder
from app.services.scenario_engine import ScenarioEngine


class CompoundService:
    def __init__(self, scenario: ScenarioEngine, events: EventLogService) -> None:
        self._scenario = scenario
        self._events = events

    def execute(self, body: IntentExecuteRequest) -> IntentExecuteResponse:
        if body.intent != COMPOUND_ACTION_INTENT:
            return ExecutionResponseBuilder.error(
                spoken_response="Внутренняя ошибка сценария.",
                ui_message="CompoundService called for non-compound intent.",
                error_code="internal",
                error_message="compound routing bug",
                trace={"execution_engine": "p5-compound", "intent": body.intent},
            )

        entities = dict(body.entities)
        steps_raw = entities.get("steps")
        if not isinstance(steps_raw, list) or len(steps_raw) != 2:
            self._events.append(
                "compound_error",
                "compound: invalid steps shape",
                {"reason": "steps_must_be_list_of_two"},
            )
            return ExecutionResponseBuilder.error(
                spoken_response="Составная команда задана неверно.",
                ui_message="compound_action requires entities.steps as a list of exactly two step objects.",
                error_code="compound_invalid_shape",
                error_message="steps must be a list of length 2.",
                trace={"execution_engine": "p5-compound", "phase": "validate"},
            )

        steps: list[dict[str, Any]] = []
        for i, raw in enumerate(steps_raw):
            if not isinstance(raw, dict):
                return _compound_shape_error(self._events, f"step {i} not an object")
            intent = raw.get("intent")
            ent = raw.get("entities")
            if not isinstance(intent, str) or not isinstance(ent, dict):
                return _compound_shape_error(self._events, f"step {i} missing intent or entities")
            steps.append({"intent": intent, "entities": dict(ent)})

        for s in steps:
            if s["intent"] not in P4A_EXECUTE_INTENTS:
                self._events.append(
                    "compound_error",
                    f"unsupported sub-intent {s['intent']!r}",
                    {"intent": s["intent"]},
                )
                return ExecutionResponseBuilder.error(
                    spoken_response="Составная команда содержит неподдерживаемый шаг.",
                    ui_message=f"Unsupported compound step intent: {s['intent']!r}.",
                    error_code="compound_unsupported_step",
                    error_message="Each step intent must be in the P4a execution subset.",
                    trace={"execution_engine": "p5-compound", "phase": "intent_gate"},
                )

        for idx, s in enumerate(steps):
            try:
                resolve_for_intent(s["intent"], s["entities"])
            except EntityResolutionError as e:
                self._events.append(
                    "compound_error",
                    f"preflight step {idx}: {e.code}",
                    {"step": idx, "code": e.code},
                )
                return ExecutionResponseBuilder.error(
                    spoken_response="Составная команда не прошла проверку.",
                    ui_message=e.message,
                    error_code=f"compound_preflight_{e.code}",
                    error_message=e.message,
                    trace={"execution_engine": "p5-compound", "phase": "preflight", "step": idx},
                )

        self._events.append(
            "compound_started",
            "compound: executing two steps",
            {"steps": [s["intent"] for s in steps]},
        )

        results: list[IntentExecuteResponse] = []
        for idx, s in enumerate(steps):
            sub = IntentExecuteRequest(
                intent=s["intent"],
                source=body.source,
                utterance=body.utterance,
                entities=s["entities"],
                confidence=body.confidence,
                requires_clarification=False,
                meta=dict(body.meta) | {"compound_parent": COMPOUND_ACTION_INTENT, "compound_step": idx},
            )
            res = self._scenario.execute(sub)
            results.append(res)
            if res.status != "success":
                self._events.append(
                    "compound_partial_failure" if idx == 1 else "compound_error",
                    f"step {idx} status={res.status}",
                    {"step": idx, "error_code": res.error_code},
                )
                return _merge_partial_or_fatal_from_response(results, idx, res, self._events)

        self._events.append(
            "compound_success",
            "compound: both steps ok",
            {"affected": [e for r in results for e in r.affected_entities]},
        )
        spoken = f"{results[0].spoken_response} {results[1].spoken_response}".strip()
        ui = f"{results[0].ui_message} | {results[1].ui_message}"
        affected = [*results[0].affected_entities, *results[1].affected_entities]
        trace = {
            "execution_engine": "p5-compound",
            "intent": COMPOUND_ACTION_INTENT,
            "steps": [r.trace for r in results],
        }
        return ExecutionResponseBuilder.success(
            spoken_response=spoken,
            ui_message=ui,
            affected_entities=affected,
            trace=trace,
        )


def _compound_shape_error(events: EventLogService, msg: str) -> IntentExecuteResponse:
    events.append("compound_error", msg, {})
    return ExecutionResponseBuilder.error(
        spoken_response="Составная команда задана неверно.",
        ui_message=msg,
        error_code="compound_invalid_shape",
        error_message=msg,
        trace={"execution_engine": "p5-compound", "phase": "validate"},
    )


def _merge_partial_or_fatal_from_response(
    prior: list[IntentExecuteResponse],
    failed_idx: int,
    failed: IntentExecuteResponse,
    events: EventLogService,
) -> IntentExecuteResponse:
    if failed_idx == 0:
        return failed
    r0 = prior[0]
    events.append(
        "compound_partial_failure",
        f"step {failed_idx} error",
        {"error_code": failed.error_code},
    )
    return ExecutionResponseBuilder.error(
        spoken_response="Первая часть выполнена, вторая не удалась.",
        ui_message=f"Step 0 ok; step 1: {failed.ui_message}",
        error_code="compound_partial_failure",
        error_message=failed.error_message or "",
        affected_entities=list(r0.affected_entities),
        trace={
            "execution_engine": "p5-compound",
            "phase": "execute",
            "failed_step": failed_idx,
            "first_step_trace": r0.trace,
            "second_trace": failed.trace,
        },
    )
