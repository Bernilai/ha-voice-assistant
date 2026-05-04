from fastapi import APIRouter, Query

from app.api.deps import AppStateDep
from app.models.events import EventsListResponse

router = APIRouter(prefix="/api", tags=["events"])


@router.get("/events", response_model=EventsListResponse)
def list_events(ctx: AppStateDep, limit: int = Query(50, ge=1, le=200)) -> EventsListResponse:
    return EventsListResponse(events=ctx.event_log.list_newest_first(limit))
