from fastapi import APIRouter

from app.api.deps import AppStateDep
from app.models.intents import (
    IntentClarifyRequest,
    IntentExecuteRequest,
    IntentExecuteResponse,
    IntentInterpretRequest,
    IntentInterpretResponse,
)
from app.intents.constants import P4B_STATUS_INTENTS
from app.services.interpret_stub import interpret_text

router = APIRouter(prefix="/api/intents", tags=["intents"])


@router.post("/interpret", response_model=IntentInterpretResponse)
def interpret(body: IntentInterpretRequest, ctx: AppStateDep) -> IntentInterpretResponse:
    result = interpret_text(body.text)
    ctx.event_log.append(
        "intent_interpret",
        "Stub interpretation",
        {"status": result.status, "canonical_intent": result.canonical_intent},
    )
    return result


@router.post("/execute", response_model=IntentExecuteResponse)
def execute(body: IntentExecuteRequest, ctx: AppStateDep) -> IntentExecuteResponse:
    if body.intent in P4B_STATUS_INTENTS:
        return ctx.status.query(body)
    return ctx.execution.execute(body)


@router.post("/clarify", response_model=IntentExecuteResponse)
def clarify(body: IntentClarifyRequest, ctx: AppStateDep) -> IntentExecuteResponse:
    ctx.event_log.append(
        "intent_clarify_attempt",
        "Clarification follow-up",
        {"session_id": body.session_id, "reply": body.reply},
    )
    return ctx.clarification_service.continue_session(body.session_id, body.reply)
