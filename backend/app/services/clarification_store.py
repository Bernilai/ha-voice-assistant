"""In-memory clarification sessions with explicit TTL (P5)."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class ClarificationSessionRecord:
    session_id: str
    pending_intent: str
    candidate_entity_ids: tuple[str, ...]
    original_entities: dict[str, Any]
    utterance: str
    expires_at: float


class ClarificationStore:
    def __init__(self, ttl_seconds: float = 120.0, *, clock: Callable[[], float] | None = None) -> None:
        self._ttl = ttl_seconds
        self._clock = clock or time.time
        self._sessions: dict[str, ClarificationSessionRecord] = {}

    @property
    def ttl_seconds(self) -> float:
        return self._ttl

    def now(self) -> float:
        return self._clock()

    def new_session_id(self) -> str:
        return str(uuid.uuid4())

    def put(self, record: ClarificationSessionRecord) -> None:
        self._sessions[record.session_id] = record

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def clear(self) -> None:
        self._sessions.clear()

    def peek(self, session_id: str) -> tuple[Literal["ok", "missing", "expired"], ClarificationSessionRecord | None]:
        """Return session state without deleting (expired sessions are removed)."""
        rec = self._sessions.get(session_id)
        if rec is None:
            return "missing", None
        if self._clock() >= rec.expires_at:
            del self._sessions[session_id]
            return "expired", None
        return "ok", rec
