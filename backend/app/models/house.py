"""Normalized house state models (P1 stub matches P2 entity ids)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DeviceState(BaseModel):
    entity_id: str
    domain: str
    name: str
    state: str
    device_class: str | None = None


class SensorState(BaseModel):
    entity_id: str
    kind: str
    name: str
    state: str
    unit: str | None = None


class RoomState(BaseModel):
    room_id: str
    name: str
    devices: list[DeviceState] = Field(default_factory=list)
    sensors: list[SensorState] = Field(default_factory=list)


class HouseStatePayload(BaseModel):
    """Payload for GET /api/state/house."""

    version: str = "p3-ha"
    rooms: list[RoomState]
