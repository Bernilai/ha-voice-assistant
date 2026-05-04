"""Centralized construction of POST /api/intents/execute responses."""

from __future__ import annotations

from typing import Any

from app.models.house import DeviceState, RoomState, SensorState
from app.models.intents import IntentExecuteResponse


class ExecutionResponseBuilder:
    @staticmethod
    def success(
        *,
        spoken_response: str,
        ui_message: str,
        affected_entities: list[str],
        trace: dict[str, Any],
    ) -> IntentExecuteResponse:
        return IntentExecuteResponse(
            status="success",
            spoken_response=spoken_response,
            ui_message=ui_message,
            affected_entities=affected_entities,
            queried_entities=[],
            trace=trace,
            error_code=None,
            error_message=None,
            clarification=None,
        )

    @staticmethod
    def error(
        *,
        spoken_response: str,
        ui_message: str,
        error_code: str,
        error_message: str,
        affected_entities: list[str] | None = None,
        trace: dict[str, Any] | None = None,
    ) -> IntentExecuteResponse:
        return IntentExecuteResponse(
            status="error",
            spoken_response=spoken_response,
            ui_message=ui_message,
            affected_entities=affected_entities or [],
            queried_entities=[],
            trace=trace or {},
            error_code=error_code,
            error_message=error_message,
            clarification=None,
        )

    @staticmethod
    def clarification_required(
        *,
        spoken_response: str,
        ui_message: str,
        clarification: dict[str, Any],
        trace: dict[str, Any],
    ) -> IntentExecuteResponse:
        return IntentExecuteResponse(
            status="clarification_required",
            spoken_response=spoken_response,
            ui_message=ui_message,
            affected_entities=[],
            queried_entities=[],
            trace=trace,
            error_code=None,
            error_message=None,
            clarification=clarification,
        )


# --- P4b status (read-only): compact Russian UX strings ---

_DEVICE_SUMMARY_LABEL: dict[str, str] = {
    "light.living_room_main": "основной свет",
    "light.living_room_floor_lamp": "торшер",
    "cover.living_room_curtains": "шторы",
    "light.kitchen_main": "основной свет",
    "light.kitchen_accent": "подсветка",
    "switch.kitchen_kettle": "чайник",
    "light.bedroom_main": "основной свет",
    "light.bedroom_bedside": "прикроватный",
    "cover.bedroom_curtains": "шторы",
    "switch.bedroom_heater": "обогреватель",
    "climate.bedroom_heater": "климат",
}


def _device_value_ru(device: DeviceState) -> str:
    st = (device.state or "").lower()
    if device.domain == "light" or device.domain == "switch":
        return "вкл" if st == "on" else "выкл" if st == "off" else st
    if device.domain == "cover":
        if st == "open":
            return "открыты"
        if st in ("closed", "closing", "opening"):
            return "закрыты" if st == "closed" else st
        return st or "?"
    if device.domain == "climate":
        return st or "?"
    return st or "?"


def _sensor_value_ru(sensor: SensorState) -> str:
    st = sensor.state or ""
    if sensor.entity_id.startswith("binary_sensor."):
        on = st.lower() == "on"
        if sensor.kind == "motion":
            return "есть" if on else "нет"
        if sensor.kind == "window":
            return "открыто" if on else "закрыто"
        return "да" if on else "нет"
    unit = sensor.unit or ""
    return f"{st}{unit}".strip()


def _sensor_summary_label(sensor: SensorState) -> str:
    return {
        "temperature": "темп.",
        "motion": "движ.",
        "window": "окно",
        "humidity": "влажн.",
    }.get(sensor.kind, sensor.kind)


class StatusResponseBuilder:
    """HTTP 200 bodies for P4b status queries; uses queried_entities, leaves affected_entities empty."""

    @staticmethod
    def success(
        *,
        spoken_response: str,
        ui_message: str,
        queried_entities: list[str],
        trace: dict[str, Any],
    ) -> IntentExecuteResponse:
        return IntentExecuteResponse(
            status="success",
            spoken_response=spoken_response,
            ui_message=ui_message,
            affected_entities=[],
            queried_entities=queried_entities,
            trace=trace,
            error_code=None,
            error_message=None,
            clarification=None,
        )

    @staticmethod
    def error(
        *,
        spoken_response: str,
        ui_message: str,
        error_code: str,
        error_message: str,
        trace: dict[str, Any] | None = None,
    ) -> IntentExecuteResponse:
        return IntentExecuteResponse(
            status="error",
            spoken_response=spoken_response,
            ui_message=ui_message,
            affected_entities=[],
            queried_entities=[],
            trace=trace or {},
            error_code=error_code,
            error_message=error_message,
            clarification=None,
        )

    @staticmethod
    def format_room_summary(room: RoomState) -> tuple[str, str]:
        parts: list[str] = []
        for d in room.devices:
            label = _DEVICE_SUMMARY_LABEL.get(d.entity_id, d.entity_id.split(".")[-1])
            parts.append(f"{label} {_device_value_ru(d)}")
        for s in room.sensors:
            parts.append(f"{_sensor_summary_label(s)} {_sensor_value_ru(s)}")
        compact = "; ".join(parts)
        ui = f"{room.name}: {compact}"
        spoken = f"{room.name}: {compact}"
        return spoken, ui

    @staticmethod
    def format_device_line(device: DeviceState) -> tuple[str, str]:
        val = _device_value_ru(device)
        ui = f"{device.name}: {val} ({device.entity_id})"
        spoken = f"{device.name} — {val}."
        return spoken, ui

    @staticmethod
    def format_sensor_line(sensor: SensorState) -> tuple[str, str]:
        val = _sensor_value_ru(sensor)
        ui = f"{sensor.name}: {val} ({sensor.entity_id})"
        spoken = f"{sensor.name} — {val}."
        return spoken, ui
