"""P9 optional voice / transcript bridge — narrow adapter over interpret + execute."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.models.intents import IntentExecuteResponse, IntentInterpretResponse


class VoiceTranscriptRequest(BaseModel):
    """POST /api/voice/transcript — simulate HA Assist transcript delivery into the text-first stack."""

    transcript: str = Field(..., min_length=1, description="Raw transcript text (same surface as interpret text)")


class VoiceStatusResponse(BaseModel):
    """GET /api/voice/status — operator metadata; does not imply microphone or cloud STT availability."""

    integration_kind: Literal["ha_assist_plus_transcript_bridge"] = "ha_assist_plus_transcript_bridge"
    bridge_enabled: bool
    transcript_endpoint_available: bool
    ha_assist_local_path: str = Field(
        description="How HA Assist custom sentences map to intent_script in ha/ (HA-local execution).",
    )
    transcript_bridge_path: str = Field(
        description="How POST /api/voice/transcript reuses interpret + execute with a narrow allowlist.",
    )
    supported_transcript_phrases_ru: list[str] = Field(default_factory=list)
    intentionally_unsupported_via_transcript: list[str] = Field(default_factory=list)
    clarification_policy_ru: str


class VoiceProcessResponse(BaseModel):
    """Result of POST /api/voice/transcript — honest about whether backend execution ran."""

    outcome: Literal["executed", "fallback_to_text", "bridge_disabled"]
    execution_claimed: bool = Field(
        description="True only when execute/status ran and returned success or error (not clarification).",
    )
    transcript: str
    message_ru: str
    voice_path: Literal["transcript_bridge"] = "transcript_bridge"
    interpret: IntentInterpretResponse | None = None
    policy_reason: str | None = Field(
        default=None,
        description="Machine-stable reason when outcome is fallback or bridge_disabled.",
    )
    execute: IntentExecuteResponse | None = None


def voice_process_bridge_disabled(transcript: str) -> VoiceProcessResponse:
    return VoiceProcessResponse(
        outcome="bridge_disabled",
        execution_claimed=False,
        transcript=transcript,
        message_ru="Голосовой мост отключён (VOICE_BRIDGE_ENABLED). Используйте текстовую консоль или прямые вызовы /api/intents/*.",
        interpret=None,
        policy_reason="bridge_disabled",
        execute=None,
    )


def voice_process_fallback(
    *,
    transcript: str,
    message_ru: str,
    policy_reason: str,
    interpret: IntentInterpretResponse | None = None,
    execute: IntentExecuteResponse | None = None,
) -> VoiceProcessResponse:
    return VoiceProcessResponse(
        outcome="fallback_to_text",
        execution_claimed=False,
        transcript=transcript,
        message_ru=message_ru,
        interpret=interpret,
        policy_reason=policy_reason,
        execute=execute,
    )


def voice_process_executed(
    *,
    transcript: str,
    message_ru: str,
    interpret: IntentInterpretResponse,
    execute: IntentExecuteResponse,
) -> VoiceProcessResponse:
    return VoiceProcessResponse(
        outcome="executed",
        execution_claimed=True,
        transcript=transcript,
        message_ru=message_ru,
        interpret=interpret,
        policy_reason=None,
        execute=execute,
    )
