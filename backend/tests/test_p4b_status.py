"""P4b read-only status layer: HA-backed queries, no writes, deterministic on mock."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.integrations.ha_client import HomeAssistantUnavailableError
from app.main import app
from app.services.status_service import StatusService


def _execute(client: TestClient, intent: str, entities: dict) -> dict:
    r = client.post(
        "/api/intents/execute",
        json={
            "intent": intent,
            "source": "text",
            "utterance": "test",
            "entities": entities,
            "confidence": 1.0,
            "requires_clarification": False,
            "meta": {},
        },
    )
    assert r.status_code == 200
    return r.json()


def test_get_room_status_kitchen_compact_summary(client: TestClient) -> None:
    client.post("/api/demo/reset")
    out = _execute(client, "get_room_status", {"room": "kitchen"})
    assert out["status"] == "success"
    assert out["affected_entities"] == []
    assert "light.kitchen_main" in out["queried_entities"]
    assert "sensor.kitchen_temperature" in out["queried_entities"]
    assert out["trace"]["status_engine"] == "p4b-status"
    assert out["trace"]["intent"] == "get_room_status"
    assert "Кухня" in out["ui_message"]
    assert "основной свет" in out["ui_message"]


def test_get_device_status_kitchen_primary_light(client: TestClient) -> None:
    client.post("/api/demo/reset")
    client.post(
        "/api/intents/execute",
        json={
            "intent": "turn_on_device",
            "source": "text",
            "utterance": "x",
            "entities": {
                "room": "kitchen",
                "device_type": "light",
                "target_entity_id": "light.kitchen_main",
            },
            "confidence": 1.0,
            "requires_clarification": False,
            "meta": {},
        },
    )
    out = _execute(client, "get_device_status", {"room": "kitchen", "device_type": "light"})
    assert out["status"] == "success"
    assert out["queried_entities"] == ["light.kitchen_main"]
    assert "вкл" in out["ui_message"].lower() or "Вкл" in out["ui_message"]
    assert "light.kitchen_main" in out["ui_message"]


def test_get_sensor_status_kitchen_temperature(client: TestClient) -> None:
    client.post("/api/demo/reset")
    out = _execute(client, "get_sensor_status", {"room": "kitchen", "sensor_kind": "temperature"})
    assert out["status"] == "success"
    assert out["queried_entities"] == ["sensor.kitchen_temperature"]
    assert "22" in out["ui_message"] or "22" in out["spoken_response"]


def test_get_sensor_status_temperature_for_all_target_rooms(client: TestClient) -> None:
    client.post("/api/demo/reset")
    for room, entity_id in (
        ("kitchen", "sensor.kitchen_temperature"),
        ("bedroom", "sensor.bedroom_temperature"),
        ("living_room", "sensor.living_room_temperature"),
    ):
        out = _execute(client, "get_sensor_status", {"room": room, "sensor_kind": "temperature"})
        assert out["status"] == "success"
        assert out["queried_entities"] == [entity_id]


def test_get_device_status_unsupported_device_type(client: TestClient) -> None:
    client.post("/api/demo/reset")
    out = _execute(client, "get_device_status", {"room": "kitchen", "device_type": "switch"})
    assert out["status"] == "error"
    assert out["error_code"] == "unsupported_target"
    assert out["queried_entities"] == []


def test_status_query_does_not_call_ha_services(client: TestClient) -> None:
    client.post("/api/demo/reset")
    mock = client.app.state.app_state.ha_client
    n_calls = len(mock.service_calls)
    _execute(client, "get_room_status", {"room": "living_room"})
    _execute(client, "get_device_status", {"room": "bedroom", "device_type": "light"})
    _execute(client, "get_sensor_status", {"room": "bedroom", "sensor_kind": "humidity"})
    assert len(mock.service_calls) == n_calls


def test_status_query_does_not_mutate_device_state(client: TestClient) -> None:
    client.post("/api/demo/reset")
    client.post(
        "/api/intents/execute",
        json={
            "intent": "turn_on_device",
            "source": "text",
            "utterance": "x",
            "entities": {
                "room": "kitchen",
                "device_type": "light",
                "target_entity_id": "light.kitchen_main",
            },
            "confidence": 1.0,
            "requires_clarification": False,
            "meta": {},
        },
    )
    house_before = client.get("/api/state/house").json()
    _execute(client, "get_room_status", {"room": "kitchen"})
    house_after = client.get("/api/state/house").json()
    assert house_before == house_after


def test_get_sensor_status_unsupported_pair(client: TestClient) -> None:
    client.post("/api/demo/reset")
    out = _execute(client, "get_sensor_status", {"room": "kitchen", "sensor_kind": "humidity"})
    assert out["status"] == "error"
    assert out["error_code"] == "unsupported_target"


def test_status_ha_read_failure_returns_error_body() -> None:
    from tests.mock_ha_client import MockHomeAssistantClient

    class Flaky(MockHomeAssistantClient):
        def get_states(self):
            raise HomeAssistantUnavailableError("ha_unreachable", "Could not reach Home Assistant.")

    with TestClient(app) as c:
        st = c.app.state.app_state
        st.ha_client = Flaky()
        st.rebind_ha_stack()
        st.status = StatusService(house_supplier=st.house_payload_from_ha, events=st.event_log)
        c.post("/api/demo/reset")
        r = c.post(
            "/api/intents/execute",
            json={
                "intent": "get_room_status",
                "source": "text",
                "utterance": "x",
                "entities": {"room": "kitchen"},
                "confidence": 1.0,
                "requires_clarification": False,
                "meta": {},
            },
        )
    assert r.status_code == 200
    out = r.json()
    assert out["status"] == "error"
    assert out["error_code"] == "ha_unreachable"
    assert out["trace"].get("phase") == "ha_read"
