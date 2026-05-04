"""Intent / interpret request and response models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class IntentInterpretRequest(BaseModel):
    """POST /api/intents/interpret — natural text in, stub interpretation out."""

    text: str = Field(..., min_length=1, description="Raw user command text")


class IntentInterpretResponse(BaseModel):
    raw_text: str
    normalized_text: str
    canonical_intent: str | None = None
    entities: dict[str, Any] = Field(default_factory=dict)
    status: Literal["success", "clarification_required", "unsupported"]
    clarification: dict[str, Any] | None = None


class IntentExecuteRequest(BaseModel):
    """Aligned with docs/api-contracts.md canonical payload."""

    intent: str
    source: str = "text"
    utterance: str
    entities: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    requires_clarification: bool = False
    meta: dict[str, Any] = Field(default_factory=dict)


class IntentExecuteResponse(BaseModel):
    status: Literal["success", "error", "clarification_required"]
    spoken_response: str
    ui_message: str
    affected_entities: list[str] = Field(default_factory=list)
    queried_entities: list[str] = Field(
        default_factory=list,
        description="HA entity_ids read for status intents (P4b); empty for execution writes.",
    )
    trace: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
    clarification: dict[str, Any] | None = Field(
        default=None,
        description="P5: present when status is clarification_required (session id, options, TTL hint).",
    )


class IntentClarifyRequest(BaseModel):
    """POST /api/intents/clarify — continue after clarification_required (P5)."""

    session_id: str = Field(..., min_length=1)
    reply: str = Field(..., min_length=1)
