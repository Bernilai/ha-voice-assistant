"""P4b: read-only status queries from HA-backed house state (no writes, no execution core)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.integrations.ha_client import HomeAssistantIntegrationError
from app.models.house import HouseStatePayload, RoomState, SensorState
from app.models.intents import IntentExecuteRequest, IntentExecuteResponse
from app.services.event_log import EventLogService
from app.services.response_builder import StatusResponseBuilder
from app.services.status_resolver import (
    ResolvedDeviceStatus,
    ResolvedRoomStatus,
    ResolvedSensorStatus,
    StatusResolutionError,
    resolve_status_intent,
)


class StatusService:
    """Assembles status answers from the same HA-backed path as GET /api/state/house."""

    def __init__(
        self,
        *,
        house_supplier: Callable[[], HouseStatePayload],
        events: EventLogService,
    ) -> None:
        self._house = house_supplier
        self._events = events

    def query(self, payload: IntentExecuteRequest) -> IntentExecuteResponse:
        intent = payload.intent
        entities = dict(payload.entities)
        trace_base: dict[str, Any] = {
            "status_engine": "p4b-status",
            "intent": intent,
            "entities": entities,
        }

        self._events.append(
            "intent_status_attempt",
            f"Status query: {intent}",
            {"intent": intent, "entities": entities, "utterance": payload.utterance},
        )

        try:
            resolved = resolve_status_intent(intent, entities)
        except StatusResolutionError as e:
            self._events.append(
                "intent_status_error",
                f"Status resolution failed: {e.code}",
                {"intent": intent, "code": e.code, "message": e.message},
            )
            return StatusResponseBuilder.error(
                spoken_response="Запрос статуса не сопоставлен с известной целью.",
                ui_message=e.message,
                error_code=e.code,
                error_message=e.message,
                trace=trace_base | {"phase": "resolve", "resolution_error": e.code},
            )

        try:
            house = self._house()
        except HomeAssistantIntegrationError as e:
            self._events.append(
                "intent_status_error",
                f"HA read failed: {e.code}",
                {"intent": intent, "code": e.code},
            )
            return StatusResponseBuilder.error(
                spoken_response="Не удалось прочитать состояние из Home Assistant.",
                ui_message=e.message,
                error_code=e.code,
                error_message=e.message,
                trace=trace_base | {"phase": "ha_read", "ha_error": e.code},
            )

        if isinstance(resolved, ResolvedRoomStatus):
            out = self._room_status(house, resolved, trace_base)
        elif isinstance(resolved, ResolvedDeviceStatus):
            out = self._device_status(house, resolved, trace_base)
        else:
            out = self._sensor_status(house, resolved, trace_base)

        if out.status == "success":
            self._events.append(
                "intent_status_success",
                f"Status ok: {intent}",
                {"intent": intent, "queried_entities": out.queried_entities},
            )
        return out

    def _find_room(self, house: HouseStatePayload, room_id: str) -> RoomState | None:
        for r in house.rooms:
            if r.room_id == room_id:
                return r
        return None

    def _room_status(
        self,
        house: HouseStatePayload,
        resolved: ResolvedRoomStatus,
        trace_base: dict[str, Any],
    ) -> IntentExecuteResponse:
        room = self._find_room(house, resolved.room_id)
        if room is None:
            return StatusResponseBuilder.error(
                spoken_response="Комната не найдена в текущей модели дома.",
                ui_message=f"Room {resolved.room_id!r} missing from house payload.",
                error_code="internal",
                error_message="House mapper did not include the resolved room.",
                trace=trace_base | {"phase": "assemble", "room_id": resolved.room_id},
            )
        spoken, ui = StatusResponseBuilder.format_room_summary(room)
        entity_ids = [d.entity_id for d in room.devices] + [s.entity_id for s in room.sensors]
        trace = trace_base | {"room_id": resolved.room_id, "room_name": room.name}
        return StatusResponseBuilder.success(
            spoken_response=spoken,
            ui_message=ui,
            queried_entities=entity_ids,
            trace=trace,
        )

    def _device_status(
        self,
        house: HouseStatePayload,
        resolved: ResolvedDeviceStatus,
        trace_base: dict[str, Any],
    ) -> IntentExecuteResponse:
        room = self._find_room(house, resolved.room_id)
        if room is None:
            return StatusResponseBuilder.error(
                spoken_response="Комната не найдена в текущей модели дома.",
                ui_message=f"Room {resolved.room_id!r} missing from house payload.",
                error_code="internal",
                error_message="House mapper did not include the resolved room.",
                trace=trace_base | {"phase": "assemble", "room_id": resolved.room_id},
            )
        device = next((d for d in room.devices if d.entity_id == resolved.entity_id), None)
        if device is None:
            return StatusResponseBuilder.error(
                spoken_response="Устройство не найдено в данных комнаты.",
                ui_message=f"Entity {resolved.entity_id!r} not in room devices.",
                error_code="internal",
                error_message="Device missing from normalized room (unexpected for MVP).",
                trace=trace_base | {"phase": "assemble", "resolved_entity_id": resolved.entity_id},
            )
        spoken, ui = StatusResponseBuilder.format_device_line(device)
        trace = trace_base | {
            "room_id": resolved.room_id,
            "device_type": resolved.device_type,
            "resolved_entity_id": resolved.entity_id,
        }
        return StatusResponseBuilder.success(
            spoken_response=spoken,
            ui_message=ui,
            queried_entities=[resolved.entity_id],
            trace=trace,
        )

    def _sensor_status(
        self,
        house: HouseStatePayload,
        resolved: ResolvedSensorStatus,
        trace_base: dict[str, Any],
    ) -> IntentExecuteResponse:
        room = self._find_room(house, resolved.room_id)
        if room is None:
            return StatusResponseBuilder.error(
                spoken_response="Комната не найдена в текущей модели дома.",
                ui_message=f"Room {resolved.room_id!r} missing from house payload.",
                error_code="internal",
                error_message="House mapper did not include the resolved room.",
                trace=trace_base | {"phase": "assemble", "room_id": resolved.room_id},
            )
        sensor = next((s for s in room.sensors if s.entity_id == resolved.entity_id), None)
        if sensor is None:
            return StatusResponseBuilder.error(
                spoken_response="Датчик не найден в данных комнаты.",
                ui_message=f"Entity {resolved.entity_id!r} not in room sensors.",
                error_code="internal",
                error_message="Sensor missing from normalized room (unexpected for MVP).",
                trace=trace_base | {"phase": "assemble", "resolved_entity_id": resolved.entity_id},
            )
        spoken, ui = StatusResponseBuilder.format_sensor_line(sensor)
        trace = trace_base | {
            "room_id": resolved.room_id,
            "sensor_kind": resolved.sensor_kind,
            "resolved_entity_id": resolved.entity_id,
        }
        return StatusResponseBuilder.success(
            spoken_response=spoken,
            ui_message=ui,
            queried_entities=[resolved.entity_id],
            trace=trace,
        )
