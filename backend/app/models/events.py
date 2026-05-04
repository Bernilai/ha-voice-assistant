"""Event log models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EventItem(BaseModel):
    id: str
    timestamp: str
    type: str
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventsListResponse(BaseModel):
    events: list[EventItem]
    order: str = "newest_first"
