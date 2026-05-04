"""P5: thin routing for compound_action, light ambiguity, and single P4a execution."""

from __future__ import annotations

from app.intents.constants import COMPOUND_ACTION_INTENT
from app.models.intents import IntentExecuteRequest, IntentExecuteResponse
from app.services.clarification_service import ClarificationService
from app.services.compound_service import CompoundService
from app.services.entity_resolver import (
    EntityResolutionError,
    infer_room_for_light_entity,
    list_all_mvp_light_entity_ids,
    list_light_entity_ids_for_room,
)
from app.services.event_log import EventLogService
from app.services.scenario_engine import ScenarioEngine


class ExecutionOrchestrator:
    def __init__(
        self,
        scenario: ScenarioEngine,
        compound: CompoundService,
        clarification: ClarificationService,
        events: EventLogService,
    ) -> None:
        self._scenario = scenario
        self._compound = compound
        self._clarification = clarification
        self._events = events

    def execute(self, body: IntentExecuteRequest) -> IntentExecuteResponse:
        if body.intent == COMPOUND_ACTION_INTENT:
            return self._compound.execute(body)
        if body.intent not in ("turn_on_device", "turn_off_device"):
            return self._scenario.execute(body)

        entities = dict(body.entities)
        device_type = entities.get("device_type")
        if device_type != "light":
            return self._scenario.execute(body)

        room = entities.get("room")
        tid = entities.get("target_entity_id")
        if isinstance(tid, str):
            merged = dict(entities)
            if not isinstance(room, str):
                inferred = infer_room_for_light_entity(tid)
                if inferred is None:
                    return self._scenario.execute(body)
                merged["room"] = inferred
            return self._scenario.execute(body.model_copy(update={"entities": merged}))

        lights: tuple[str, ...]
        try:
            if isinstance(room, str):
                lights = list_light_entity_ids_for_room(room)
            elif room is None:
                lights = list_all_mvp_light_entity_ids()
            else:
                return self._scenario.execute(body)
        except EntityResolutionError:
            return self._scenario.execute(body)

        if len(lights) <= 1:
            only = lights[0] if lights else None
            if only is None:
                return self._scenario.execute(body)
            return self._scenario.execute(
                body.model_copy(update={"entities": {**entities, "target_entity_id": only}}),
            )

        self._events.append(
            "intent_execute_attempt",
            f"Execute attempt: {body.intent}",
            {
                "intent": body.intent,
                "entities": entities,
                "utterance": body.utterance,
                "phase": "ambiguity",
                "clarification_pending": True,
            },
        )
        self._events.append(
            "ambiguity_detected",
            f"intent={body.intent} candidates={len(lights)}",
            {"intent": body.intent, "candidate_entity_ids": list(lights), "room": room},
        )
        return self._clarification.create_ambiguity_response(
            pending_intent=body.intent,
            candidate_entity_ids=lights,
            original_entities=entities,
            utterance=body.utterance,
            trace_base={"intent": body.intent, "entities": entities},
        )
