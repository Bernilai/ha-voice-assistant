from fastapi import APIRouter, HTTPException

from app.api.deps import AppStateDep
from app.integrations.ha_client import HomeAssistantIntegrationError
from app.models.house import HouseStatePayload

router = APIRouter(prefix="/api", tags=["state"])


@router.get("/state/house", response_model=HouseStatePayload)
def get_house_state(ctx: AppStateDep) -> HouseStatePayload:
    try:
        return ctx.house_payload_from_ha()
    except HomeAssistantIntegrationError as e:
        raise HTTPException(
            status_code=503,
            detail={"code": e.code, "message": e.message},
        ) from None
