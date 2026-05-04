"""Smart Home MVP API — P3 house reads + P4a execution + P4b status + P5 ambiguity/compound + baseline reset."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import demo, events, health, intents, state, voice
from app.state import AppState


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.app_state = AppState()
    app.state.app_state.event_log.append(
        "system",
        "P5 API ready (HA-backed reads/writes, ambiguity + compound orchestration)",
        {},
    )
    yield


app = FastAPI(title="Smart Home MVP API", version="0.1.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(state.router)
app.include_router(events.router)
app.include_router(intents.router)
app.include_router(demo.router)
app.include_router(voice.router)
