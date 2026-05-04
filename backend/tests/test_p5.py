"""P5: ambiguity, clarification TTL/continuation, compound_action, event log."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.clarification_store import ClarificationStore

from tests.mock_ha_client import MockHomeAssistantClient


def _ev_types(client: TestClient, limit: int = 80) -> list[str]:
    ev = client.get("/api/events", params={"limit": limit}).json()["events"]
    return [e["type"] for e in ev]


def test_ambiguous_kitchen_light_returns_clarification_required(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post(
        "/api/intents/execute",
        json={
            "intent": "turn_off_device",
            "source": "text",
            "utterance": "выключи свет на кухне",
            "entities": {"room": "kitchen", "device_type": "light"},
            "confidence": 1.0,
            "requires_clarification": False,
            "meta": {},
        },
    )
    assert r.status_code == 200
    out = r.json()
    assert out["status"] == "clarification_required"
    assert out["clarification"] is not None
    assert out["clarification"]["pending_intent"] == "turn_off_device"
    opts = out["clarification"]["options"]
    assert len(opts) == 2
    ids = {o["id"] for o in opts}
    assert ids == {"light.kitchen_main", "light.kitchen_accent"}
    types = _ev_types(client)
    assert "intent_execute_attempt" in types
    assert "ambiguity_detected" in types
    assert "clarification_created" in types


def test_clarification_follow_up_executes_target(client: TestClient) -> None:
    client.post("/api/demo/reset")
    sid = client.post(
        "/api/intents/execute",
        json={
            "intent": "turn_off_device",
            "source": "text",
            "utterance": "x",
            "entities": {"room": "kitchen", "device_type": "light"},
            "confidence": 1.0,
            "requires_clarification": False,
            "meta": {},
        },
    ).json()["clarification"]["session_id"]

    r2 = client.post("/api/intents/clarify", json={"session_id": sid, "reply": "подсветка"})
    assert r2.status_code == 200
    out2 = r2.json()
    assert out2["status"] == "success"
    assert out2["affected_entities"] == ["light.kitchen_accent"]
    assert "clarification_resolved" in _ev_types(client)
    assert "intent_execute_success" in _ev_types(client)


def test_clarification_ttl_expired(client: TestClient) -> None:
    with TestClient(app) as c:
        st = c.app.state.app_state
        clk = [0.0]
        st.ha_client = MockHomeAssistantClient()
        st.clarification_store = ClarificationStore(ttl_seconds=30.0, clock=lambda: clk[0])
        st.rebind_ha_stack()
        assert c.post("/api/demo/reset").status_code == 200

        sid = c.post(
            "/api/intents/execute",
            json={
                "intent": "turn_off_device",
                "source": "text",
                "utterance": "x",
                "entities": {"room": "living_room", "device_type": "light"},
                "confidence": 1.0,
                "requires_clarification": False,
                "meta": {},
            },
        ).json()["clarification"]["session_id"]

        clk[0] = 100.0
        r = c.post("/api/intents/clarify", json={"session_id": sid, "reply": "торшер"})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "error"
        assert body["error_code"] == "clarification_expired"
        assert "clarification_expired" in _ev_types(c)


def test_clarification_invalid_reply(client: TestClient) -> None:
    client.post("/api/demo/reset")
    sid = client.post(
        "/api/intents/execute",
        json={
            "intent": "turn_off_device",
            "source": "text",
            "utterance": "x",
            "entities": {"room": "bedroom", "device_type": "light"},
            "confidence": 1.0,
            "requires_clarification": False,
            "meta": {},
        },
    ).json()["clarification"]["session_id"]

    r = client.post("/api/intents/clarify", json={"session_id": sid, "reply": "not-a-valid-token-xyz"})
    assert r.status_code == 200
    assert r.json()["status"] == "error"
    assert r.json()["error_code"] == "clarification_reply_invalid"
    assert "clarification_failed" in _ev_types(client)


def test_compound_action_success(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post(
        "/api/intents/execute",
        json={
            "intent": "compound_action",
            "source": "text",
            "utterance": "demo",
            "entities": {
                "steps": [
                    {
                        "intent": "turn_on_device",
                        "entities": {
                            "room": "bedroom",
                            "device_type": "light",
                            "target_entity_id": "light.bedroom_main",
                        },
                    },
                    {"intent": "activate_scene", "entities": {"scene": "evening"}},
                ]
            },
            "confidence": 1.0,
            "requires_clarification": False,
            "meta": {},
        },
    )
    assert r.status_code == 200
    out = r.json()
    assert out["status"] == "success"
    assert "light.bedroom_main" in out["affected_entities"]
    assert "scene.evening" in out["affected_entities"]
    types = _ev_types(client)
    assert "compound_started" in types
    assert "compound_success" in types


def test_compound_preflight_fails_on_invalid_second_step(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post(
        "/api/intents/execute",
        json={
            "intent": "compound_action",
            "source": "text",
            "utterance": "demo",
            "entities": {
                "steps": [
                    {
                        "intent": "turn_off_device",
                        "entities": {
                            "room": "kitchen",
                            "device_type": "light",
                            "target_entity_id": "light.kitchen_main",
                        },
                    },
                    {
                        "intent": "turn_on_device",
                        "entities": {"room": "kitchen", "device_type": "switch"},
                    },
                ]
            },
            "confidence": 1.0,
            "requires_clarification": False,
            "meta": {},
        },
    )
    assert r.status_code == 200
    out = r.json()
    assert out["status"] == "error"
    assert out["error_code"] == "compound_preflight_unsupported_target"
    assert out["affected_entities"] == []
    types = _ev_types(client)
    assert "compound_error" in types
    assert "compound_started" not in types


def test_compound_partial_failure_after_first_step_ha_error() -> None:
    from app.integrations.ha_client import HomeAssistantUnavailableError
    from app.main import app

    class SecondCallFails(MockHomeAssistantClient):
        def __init__(self) -> None:
            super().__init__()
            self._n = 0

        def call_service(
            self,
            domain: str,
            service: str,
            payload: dict | None = None,
        ) -> None:
            self._n += 1
            if self._n == 2:
                raise HomeAssistantUnavailableError("ha_unreachable", "Simulated HA failure on second write.")
            super().call_service(domain, service, payload)

    with TestClient(app) as c:
        st = c.app.state.app_state
        st.ha_client = SecondCallFails()
        st.rebind_ha_stack()
        assert c.post("/api/demo/reset").status_code == 200
        r = c.post(
            "/api/intents/execute",
            json={
                "intent": "compound_action",
                "source": "text",
                "utterance": "demo",
                "entities": {
                    "steps": [
                        {
                            "intent": "turn_off_device",
                            "entities": {
                                "room": "kitchen",
                                "device_type": "light",
                                "target_entity_id": "light.kitchen_main",
                            },
                        },
                        {
                            "intent": "turn_on_device",
                            "entities": {
                                "room": "kitchen",
                                "device_type": "light",
                                "target_entity_id": "light.kitchen_accent",
                            },
                        },
                    ]
                },
                "confidence": 1.0,
                "requires_clarification": False,
                "meta": {},
            },
        )
        out = r.json()
        assert out["status"] == "error"
        assert out["error_code"] == "compound_partial_failure"
        assert out["affected_entities"] == ["light.kitchen_main"]
        ev = c.get("/api/events", params={"limit": 80}).json()["events"]
        types = [e["type"] for e in ev]
        assert "compound_started" in types
        assert "compound_partial_failure" in types


def test_cross_room_ambiguity_narrow_then_resolve(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r0 = client.post(
        "/api/intents/execute",
        json={
            "intent": "turn_off_device",
            "source": "text",
            "utterance": "свет",
            "entities": {"device_type": "light"},
            "confidence": 1.0,
            "requires_clarification": False,
            "meta": {},
        },
    ).json()
    assert r0["status"] == "clarification_required"
    assert len(r0["clarification"]["options"]) == 6

    sid1 = r0["clarification"]["session_id"]
    r1 = client.post("/api/intents/clarify", json={"session_id": sid1, "reply": "кухня"})
    assert r1.status_code == 200
    out1 = r1.json()
    assert out1["status"] == "clarification_required"
    assert len(out1["clarification"]["options"]) == 2

    sid2 = out1["clarification"]["session_id"]
    r2 = client.post("/api/intents/clarify", json={"session_id": sid2, "reply": "light.kitchen_main"})
    assert r2.json()["status"] == "success"
    assert r2.json()["affected_entities"] == ["light.kitchen_main"]
