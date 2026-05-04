from fastapi.testclient import TestClient

from app.integrations.ha_client import HomeAssistantUnavailableError
from app.integrations.ha_write_adapter import HAWriteAdapter
from app.main import app

from tests.mock_ha_client import MockHomeAssistantClient


def test_house_state_shape(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.get("/api/state/house")
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == "p3-ha"
    ids = {room["room_id"] for room in data["rooms"]}
    assert ids == {"living_room", "kitchen", "bedroom"}
    kitchen = next(x for x in data["rooms"] if x["room_id"] == "kitchen")
    ids_dev = {d["entity_id"] for d in kitchen["devices"]}
    assert "light.kitchen_main" in ids_dev


def test_house_state_ha_unavailable_returns_503() -> None:
    def fail() -> list:
        raise HomeAssistantUnavailableError("ha_unreachable", "Could not reach Home Assistant.")

    with TestClient(app) as c:
        st = c.app.state.app_state
        st.ha_client = MockHomeAssistantClient(get_states_hook=fail)
        st.ha_write = HAWriteAdapter(st.ha_client)
        r = c.get("/api/state/house")
        assert r.status_code == 503
        body = r.json()
        assert body["detail"]["code"] == "ha_unreachable"
        assert "message" in body["detail"]