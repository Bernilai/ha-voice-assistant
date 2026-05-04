"""P5: follow-up resolution for light-target clarification sessions (narrow, deterministic)."""

from __future__ import annotations

import uuid
from typing import Any

from app.models.intents import IntentExecuteRequest, IntentExecuteResponse
from app.services.entity_resolver import (
    LIGHT_CLARIFICATION_LABEL,
    LIGHT_REPLY_ALIASES,
    infer_room_for_light_entity,
    narrow_room_from_reply,
)
from app.services.clarification_store import ClarificationSessionRecord, ClarificationStore
from app.services.event_log import EventLogService
from app.services.response_builder import ExecutionResponseBuilder
from app.services.scenario_engine import ScenarioEngine


class ClarificationService:
    def __init__(
        self,
        store: ClarificationStore,
        events: EventLogService,
        scenario: ScenarioEngine,
    ) -> None:
        self._store = store
        self._events = events
        self._scenario = scenario

    def build_clarification_payload(
        self,
        *,
        session_id: str,
        pending_intent: str,
        entity_ids: tuple[str, ...],
        expires_at: float,
    ) -> dict[str, Any]:
        now = self._store.now()
        ttl_left = max(0, int(expires_at - now))
        options = [
            {
                "id": eid,
                "label": LIGHT_CLARIFICATION_LABEL.get(eid, eid),
                "room_id": _room_for_light_entity(eid),
            }
            for eid in entity_ids
        ]
        return {
            "session_id": session_id,
            "pending_intent": pending_intent,
            "options": options,
            "expires_in_seconds": ttl_left,
        }

    def create_ambiguity_response(
        self,
        *,
        pending_intent: str,
        candidate_entity_ids: tuple[str, ...],
        original_entities: dict[str, Any],
        utterance: str,
        trace_base: dict[str, Any],
    ) -> IntentExecuteResponse:
        sid = self._store.new_session_id()
        exp = self._store.now() + self._store.ttl_seconds
        rec = ClarificationSessionRecord(
            session_id=sid,
            pending_intent=pending_intent,
            candidate_entity_ids=candidate_entity_ids,
            original_entities=dict(original_entities),
            utterance=utterance,
            expires_at=exp,
        )
        self._store.put(rec)
        self._events.append(
            "clarification_created",
            f"session={sid} intent={pending_intent}",
            {
                "session_id": sid,
                "intent": pending_intent,
                "candidate_entity_ids": list(candidate_entity_ids),
            },
        )
        clar = self.build_clarification_payload(
            session_id=sid,
            pending_intent=pending_intent,
            entity_ids=candidate_entity_ids,
            expires_at=exp,
        )
        trace = trace_base | {
            "execution_engine": "p5-execute",
            "phase": "ambiguity",
            "clarification_session_id": sid,
            "ambiguous_entity_ids": list(candidate_entity_ids),
        }
        return ExecutionResponseBuilder.clarification_required(
            spoken_response="Нужно уточнение: какой именно свет?",
            ui_message="Несколько источников света подходят — выберите вариант из списка или ответьте алиасом.",
            clarification=clar,
            trace=trace,
        )

    def continue_session(self, session_id: str, reply: str) -> IntentExecuteResponse:
        status, rec = self._store.peek(session_id)
        if status == "missing":
            self._events.append(
                "clarification_failed",
                "clarify: unknown session",
                {"session_id": session_id},
            )
            return ExecutionResponseBuilder.error(
                spoken_response="Сессия уточнения не найдена.",
                ui_message="Unknown clarification session_id.",
                error_code="clarification_session_invalid",
                error_message="No pending clarification for this session_id.",
                trace={"execution_engine": "p5-clarify", "phase": "session_lookup", "session_id": session_id},
            )
        if status == "expired" or rec is None:
            self._events.append(
                "clarification_expired",
                f"session={session_id}",
                {"session_id": session_id},
            )
            return ExecutionResponseBuilder.error(
                spoken_response="Время уточнения истекло. Повторите команду.",
                ui_message="Clarification session expired.",
                error_code="clarification_expired",
                error_message="The clarification session TTL elapsed.",
                trace={"execution_engine": "p5-clarify", "phase": "expired", "session_id": session_id},
            )

        chosen = _resolve_reply_to_entity(reply, rec.candidate_entity_ids)
        if chosen is None:
            narrowed_room = narrow_room_from_reply(reply)
            if narrowed_room is not None:
                in_room = tuple(e for e in rec.candidate_entity_ids if _room_for_light_entity(e) == narrowed_room)
                if len(in_room) == 1:
                    chosen = in_room[0]
                elif len(in_room) > 1:
                    self._store.delete(session_id)
                    new_sid = str(uuid.uuid4())
                    exp = self._store.now() + self._store.ttl_seconds
                    new_rec = ClarificationSessionRecord(
                        session_id=new_sid,
                        pending_intent=rec.pending_intent,
                        candidate_entity_ids=in_room,
                        original_entities=dict(rec.original_entities) | {"room": narrowed_room},
                        utterance=rec.utterance,
                        expires_at=exp,
                    )
                    self._store.put(new_rec)
                    self._events.append(
                        "ambiguity_detected",
                        "clarify: narrowed by room",
                        {"session_id": new_sid, "room_id": narrowed_room, "candidates": list(in_room)},
                    )
                    self._events.append(
                        "clarification_created",
                        f"session={new_sid} (narrowed)",
                        {"session_id": new_sid, "intent": rec.pending_intent, "candidate_entity_ids": list(in_room)},
                    )
                    clar = self.build_clarification_payload(
                        session_id=new_sid,
                        pending_intent=rec.pending_intent,
                        entity_ids=in_room,
                        expires_at=exp,
                    )
                    trace = {
                        "execution_engine": "p5-clarify",
                        "phase": "ambiguity",
                        "clarification_session_id": new_sid,
                        "ambiguous_entity_ids": list(in_room),
                    }
                    return ExecutionResponseBuilder.clarification_required(
                        spoken_response="Уточните конкретный свет в этой комнате.",
                        ui_message="В комнате несколько светильников — выберите один из вариантов ниже.",
                        clarification=clar,
                        trace=trace,
                    )

        if chosen is None:
            self._events.append(
                "clarification_failed",
                f"clarify: no match session={session_id}",
                {"session_id": session_id, "reply": reply},
            )
            return ExecutionResponseBuilder.error(
                spoken_response="Не понял ответ. Выберите вариант из списка.",
                ui_message="Clarification reply did not match any candidate.",
                error_code="clarification_reply_invalid",
                error_message="Reply did not uniquely match a pending light candidate.",
                trace={
                    "execution_engine": "p5-clarify",
                    "phase": "reply_match",
                    "session_id": session_id,
                },
            )

        self._store.delete(session_id)
        self._events.append(
            "clarification_resolved",
            f"session={session_id} entity={chosen}",
            {"session_id": session_id, "entity_id": chosen},
        )

        entities = dict(rec.original_entities)
        entities["target_entity_id"] = chosen
        if not isinstance(entities.get("room"), str):
            inferred = infer_room_for_light_entity(chosen)
            if inferred is not None:
                entities["room"] = inferred
        req = IntentExecuteRequest(
            intent=rec.pending_intent,
            source="text",
            utterance=reply,
            entities=entities,
            confidence=1.0,
            requires_clarification=False,
            meta={"clarification_session_id": session_id},
        )
        return self._scenario.execute(req)


def _room_for_light_entity(entity_id: str) -> str:
    return infer_room_for_light_entity(entity_id) or "unknown"


def _resolve_reply_to_entity(reply: str, candidates: tuple[str, ...]) -> str | None:
    raw = reply.strip()
    if raw in candidates:
        return raw
    low = raw.lower()
    matches: list[str] = []
    for eid in candidates:
        if low == eid.lower():
            matches.append(eid)
            continue
        aliases = LIGHT_REPLY_ALIASES.get(eid, frozenset())
        if any(low == a.lower() for a in aliases):
            matches.append(eid)
    if len(matches) == 1:
        return matches[0]
    label_matches: list[str] = []
    for eid in candidates:
        label = LIGHT_CLARIFICATION_LABEL.get(eid, "")
        if label and low == label.strip().lower():
            label_matches.append(eid)
    if len(label_matches) == 1:
        return label_matches[0]
    return None
