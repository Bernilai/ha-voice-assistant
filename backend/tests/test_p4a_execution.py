"""P4a execution core: HA write path, events, baseline reset (mock HA)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.integrations.ha_client import HomeAssistantUnavailableError
from app.main import app
from tests.mock_ha_client import MockHomeAssistantClient


def test_execute_turn_off_kitchen(client: TestClient) -> None:
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
    r = client.post(
        "/api/intents/execute",
        json={
            "intent": "turn_off_device",
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
    assert r.status_code == 200
    out = r.json()
    assert out["status"] == "success"
    assert out["affected_entities"] == ["light.kitchen_main"]
    house = client.get("/api/state/house").json()
    kitchen = next(x for x in house["rooms"] if x["room_id"] == "kitchen")
    main = next(d for d in kitchen["devices"] if d["entity_id"] == "light.kitchen_main")
    assert main["state"] == "off"


def test_execute_activate_scene_movie(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post(
        "/api/intents/execute",
        json={
            "intent": "activate_scene",
            "source": "text",
            "utterance": "x",
            "entities": {"scene": "movie"},
            "confidence": 1.0,
            "requires_clarification": False,
            "meta": {},
        },
    )
    assert r.status_code == 200
    out = r.json()
    assert out["status"] == "success"
    assert out["affected_entities"] == ["scene.movie"]
    mock: MockHomeAssistantClient = client.app.state.app_state.ha_client
    assert ("scene", "turn_on", {"entity_id": "scene.movie"}) in mock.service_calls
    house = client.get("/api/state/house").json()
    lr = next(x for x in house["rooms"] if x["room_id"] == "living_room")
    main = next(d for d in lr["devices"] if d["entity_id"] == "light.living_room_main")
    assert main["state"] == "off"
    accent = next(
        d
        for d in next(x for x in house["rooms"] if x["room_id"] == "kitchen")["devices"]
        if d["entity_id"] == "light.kitchen_accent"
    )
    assert accent["state"] == "on"


def test_execute_unsupported_device_type(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post(
        "/api/intents/execute",
        json={
            "intent": "turn_on_device",
            "source": "text",
            "utterance": "x",
            "entities": {"room": "kitchen", "device_type": "switch"},
            "confidence": 1.0,
            "requires_clarification": False,
            "meta": {},
        },
    )
    assert r.status_code == 200
    out = r.json()
    assert out["status"] == "error"
    assert out["error_code"] == "unsupported_target"


def test_execute_cover_open_and_close_living_room(client: TestClient) -> None:
    client.post("/api/demo/reset")
    open_res = client.post(
        "/api/intents/execute",
        json={
            "intent": "turn_on_device",
            "source": "text",
            "utterance": "x",
            "entities": {
                "room": "living_room",
                "device_type": "curtains",
                "target_entity_id": "cover.living_room_curtains",
            },
            "confidence": 1.0,
            "requires_clarification": False,
            "meta": {},
        },
    )
    assert open_res.status_code == 200
    assert open_res.json()["status"] == "success"

    close_res = client.post(
        "/api/intents/execute",
        json={
            "intent": "turn_off_device",
            "source": "text",
            "utterance": "x",
            "entities": {
                "room": "living_room",
                "device_type": "curtains",
                "target_entity_id": "cover.living_room_curtains",
            },
            "confidence": 1.0,
            "requires_clarification": False,
            "meta": {},
        },
    )
    assert close_res.status_code == 200
    assert close_res.json()["status"] == "success"

    mock: MockHomeAssistantClient = client.app.state.app_state.ha_client
    assert ("cover", "open_cover", {"entity_id": "cover.living_room_curtains"}) in mock.service_calls
    assert ("cover", "close_cover", {"entity_id": "cover.living_room_curtains"}) in mock.service_calls


def test_execute_switch_kettle_and_heater(client: TestClient) -> None:
    client.post("/api/demo/reset")
    for intent, entities in (
        (
            "turn_on_device",
            {
                "room": "kitchen",
                "device_type": "kettle",
                "target_entity_id": "switch.kitchen_kettle",
            },
        ),
        (
            "turn_off_device",
            {
                "room": "kitchen",
                "device_type": "kettle",
                "target_entity_id": "switch.kitchen_kettle",
            },
        ),
        (
            "turn_on_device",
            {
                "room": "bedroom",
                "device_type": "heater",
                "target_entity_id": "switch.bedroom_heater",
            },
        ),
        (
            "turn_off_device",
            {
                "room": "bedroom",
                "device_type": "heater",
                "target_entity_id": "switch.bedroom_heater",
            },
        ),
    ):
        r = client.post(
            "/api/intents/execute",
            json={
                "intent": intent,
                "source": "text",
                "utterance": "x",
                "entities": entities,
                "confidence": 1.0,
                "requires_clarification": False,
                "meta": {},
            },
        )
        assert r.status_code == 200
        assert r.json()["status"] == "success"

def test_execute_unsupported_scene_key(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post(
        "/api/intents/execute",
        json={
            "intent": "activate_scene",
            "source": "text",
            "utterance": "x",
            "entities": {"scene": "nonexistent_scene_key"},
            "confidence": 1.0,
            "requires_clarification": False,
            "meta": {},
        },
    )
    assert r.status_code == 200
    out = r.json()
    assert out["status"] == "error"
    assert out["error_code"] == "unsupported_target"


def test_execute_event_log_success_and_attempt(client: TestClient) -> None:
    client.post("/api/demo/reset")
    client.post(
        "/api/intents/execute",
        json={
            "intent": "turn_on_device",
            "source": "text",
            "utterance": "x",
            "entities": {
                "room": "bedroom",
                "device_type": "light",
                "target_entity_id": "light.bedroom_main",
            },
            "confidence": 1.0,
            "requires_clarification": False,
            "meta": {},
        },
    )
    ev = client.get("/api/events", params={"limit": 50}).json()["events"]
    types = [e["type"] for e in ev]
    assert "intent_execute_attempt" in types
    assert "intent_execute_success" in types
    success = next(e for e in ev if e["type"] == "intent_execute_success")
    assert success["metadata"].get("entity_id") == "light.bedroom_main"


def test_execute_ha_error_surfaces_in_response() -> None:
    class Flaky(MockHomeAssistantClient):
        def call_service(
            self,
            domain: str,
            service: str,
            payload: dict | None = None,
        ) -> None:
            raise HomeAssistantUnavailableError("ha_unreachable", "Could not reach Home Assistant.")

    with TestClient(app) as c:
        st = c.app.state.app_state
        st.ha_client = Flaky()
        st.rebind_ha_stack()
        c.post("/api/demo/reset")
        r = c.post(
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
    assert r.status_code == 200
    out = r.json()
    assert out["status"] == "error"
    assert out["error_code"] == "ha_unreachable"


def test_demo_reset_restores_baseline_via_ha_mock(client: TestClient) -> None:
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
    house_on = client.get("/api/state/house").json()
    kitchen = next(x for x in house_on["rooms"] if x["room_id"] == "kitchen")
    assert next(d for d in kitchen["devices"] if d["entity_id"] == "light.kitchen_main")["state"] == "on"

    r = client.post("/api/demo/reset")
    assert r.status_code == 200
    house = client.get("/api/state/house").json()
    kitchen2 = next(x for x in house["rooms"] if x["room_id"] == "kitchen")
    assert next(d for d in kitchen2["devices"] if d["entity_id"] == "light.kitchen_main")["state"] == "off"


def test_execute_error_logs_intent_execute_error(client: TestClient) -> None:
    client.post("/api/demo/reset")
    client.post(
        "/api/intents/execute",
        json={
            "intent": "turn_on_device",
            "source": "text",
            "utterance": "x",
            "entities": {"room": "kitchen", "device_type": "switch"},
            "confidence": 1.0,
            "requires_clarification": False,
            "meta": {},
        },
    )
    ev = client.get("/api/events", params={"limit": 50}).json()["events"]
    assert any(e["type"] == "intent_execute_error" for e in ev)
