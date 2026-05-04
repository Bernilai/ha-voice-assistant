"""P4a: execute canonical intents via HA write adapter (HA is source of truth)."""

from __future__ import annotations

from typing import Any

from app.integrations.ha_client import HomeAssistantIntegrationError
from app.integrations.ha_write_adapter import HAWriteAdapter
from app.intents.constants import P4A_EXECUTE_INTENTS
from app.models.intents import IntentExecuteRequest, IntentExecuteResponse
from app.services.entity_resolver import (
    EntityResolutionError,
    ResolvedDeviceAction,
    ResolvedSceneAction,
    resolve_for_intent,
)
from app.services.event_log import EventLogService
from app.services.response_builder import ExecutionResponseBuilder


class ScenarioEngine:
    def __init__(self, ha_write: HAWriteAdapter, events: EventLogService) -> None:
        self._ha_write = ha_write
        self._events = events

    def execute(self, payload: IntentExecuteRequest) -> IntentExecuteResponse:
        intent = payload.intent
        entities = dict(payload.entities)
        trace_base: dict[str, Any] = {
            "execution_engine": "p4a-ha",
            "intent": intent,
            "entities": entities,
        }

        self._events.append(
            "intent_execute_attempt",
            f"Execute attempt: {intent}",
            {"intent": intent, "entities": entities, "utterance": payload.utterance},
        )

        if intent not in P4A_EXECUTE_INTENTS:
            self._events.append(
                "intent_execute_error",
                f"Unsupported intent for P4a: {intent}",
                {"intent": intent, "code": "unsupported_intent"},
            )
            return ExecutionResponseBuilder.error(
                spoken_response="Эта команда не поддерживается на этом этапе.",
                ui_message=f"P4a supports only {sorted(P4A_EXECUTE_INTENTS)}; got {intent!r}.",
                error_code="unsupported_intent",
                error_message=f"Intent {intent!r} is outside the P4a execution subset.",
                trace=trace_base | {"phase": "intent_gate"},
            )

        try:
            resolved = resolve_for_intent(intent, entities)
        except EntityResolutionError as e:
            self._events.append(
                "intent_execute_error",
                f"Resolution failed: {e.code}",
                {"intent": intent, "code": e.code, "message": e.message},
            )
            return ExecutionResponseBuilder.error(
                spoken_response="Не удалось сопоставить команду с устройством или сценой.",
                ui_message=e.message,
                error_code=e.code,
                error_message=e.message,
                trace=trace_base | {"phase": "resolve", "resolution_error": e.code},
            )

        if isinstance(resolved, ResolvedDeviceAction):
            return self._execute_device(resolved, intent, trace_base)
        return self._execute_scene(resolved, intent, trace_base)

    def _execute_device(
        self,
        resolved: ResolvedDeviceAction,
        intent: str,
        trace_base: dict[str, Any],
    ) -> IntentExecuteResponse:
        entity_id = resolved.entity_id
        action = resolved.kind
        trace = trace_base | {"resolved_entity_id": entity_id, "ha_action": action}
        try:
            if action == "turn_on":
                self._ha_write.turn_on(entity_id)
            else:
                self._ha_write.turn_off(entity_id)
        except HomeAssistantIntegrationError as e:
            self._events.append(
                "intent_execute_error",
                f"HA failure: {e.code}",
                {"intent": intent, "entity_id": entity_id, "code": e.code},
            )
            return ExecutionResponseBuilder.error(
                spoken_response="Не удалось выполнить действие в Home Assistant.",
                ui_message=e.message,
                error_code=e.code,
                error_message=e.message,
                affected_entities=[entity_id],
                trace=trace | {"ha_error": e.code},
            )

        spoken = _spoken_turn_on(entity_id) if action == "turn_on" else _spoken_turn_off(entity_id)
        self._events.append(
            "intent_execute_success",
            f"{action} {entity_id}",
            {"intent": intent, "entity_id": entity_id},
        )
        return ExecutionResponseBuilder.success(
            spoken_response=spoken,
            ui_message=f"HA {action} {entity_id}",
            affected_entities=[entity_id],
            trace=trace,
        )

    def _execute_scene(
        self,
        resolved: ResolvedSceneAction,
        intent: str,
        trace_base: dict[str, Any],
    ) -> IntentExecuteResponse:
        scene_entity_id = resolved.scene_entity_id
        trace = trace_base | {"resolved_entity_id": scene_entity_id, "ha_action": "scene.turn_on"}
        try:
            self._ha_write.activate_scene(scene_entity_id)
        except HomeAssistantIntegrationError as e:
            self._events.append(
                "intent_execute_error",
                f"HA failure: {e.code}",
                {"intent": intent, "entity_id": scene_entity_id, "code": e.code},
            )
            return ExecutionResponseBuilder.error(
                spoken_response="Не удалось выполнить действие в Home Assistant.",
                ui_message=e.message,
                error_code=e.code,
                error_message=e.message,
                affected_entities=[scene_entity_id],
                trace=trace | {"ha_error": e.code},
            )

        self._events.append(
            "intent_execute_success",
            f"activate_scene {scene_entity_id}",
            {"intent": intent, "entity_id": scene_entity_id},
        )
        return ExecutionResponseBuilder.success(
            spoken_response=_spoken_scene(scene_entity_id),
            ui_message=f"HA scene.turn_on {scene_entity_id}",
            affected_entities=[scene_entity_id],
            trace=trace,
        )


def _spoken_turn_on(entity_id: str) -> str:
    return {
        "light.kitchen_main": "Включаю основной свет на кухне.",
        "light.living_room_main": "Включаю основной свет в гостиной.",
        "light.bedroom_main": "Включаю основной свет в спальне.",
        "cover.living_room_curtains": "Открываю шторы в гостиной.",
        "cover.bedroom_curtains": "Открываю шторы в спальне.",
        "switch.kitchen_kettle": "Включаю чайник на кухне.",
        "switch.bedroom_heater": "Включаю обогреватель в спальне.",
    }.get(entity_id, "Включаю свет.")


def _spoken_turn_off(entity_id: str) -> str:
    return {
        "light.kitchen_main": "Выключаю основной свет на кухне.",
        "light.living_room_main": "Выключаю основной свет в гостиной.",
        "light.bedroom_main": "Выключаю основной свет в спальне.",
        "cover.living_room_curtains": "Закрываю шторы в гостиной.",
        "cover.bedroom_curtains": "Закрываю шторы в спальне.",
        "switch.kitchen_kettle": "Выключаю чайник на кухне.",
        "switch.bedroom_heater": "Выключаю обогреватель в спальне.",
    }.get(entity_id, "Выключаю свет.")


def _spoken_scene(scene_entity_id: str) -> str:
    return {
        "scene.movie": "Включаю режим кино.",
        "scene.good_morning": "Включаю сцену «Доброе утро».",
        "scene.evening": "Включаю вечернюю сцену.",
        "scene.away": "Включаю сцену «Я ушёл».",
    }.get(scene_entity_id, "Сцена активирована.")
