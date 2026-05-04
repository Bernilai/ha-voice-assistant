"""In-memory append-only event log (newest first on read)."""

from __future__ import annotations

import itertools
from datetime import datetime, timezone
from typing import Any

from app.models.events import EventItem


class EventLogService:
    def __init__(self) -> None:
        self._items: list[EventItem] = []
        self._id = itertools.count(1)

    def clear(self) -> None:
        self._items.clear()

    def append(self, type_: str, message: str, metadata: dict[str, Any] | None = None) -> EventItem:
        item = EventItem(
            id=str(next(self._id)),
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            type=type_,
            message=message,
            metadata=metadata or {},
        )
        self._items.append(item)
        return item

    def list_newest_first(self, limit: int = 50) -> list[EventItem]:
        return list(reversed(self._items[-limit:]))
