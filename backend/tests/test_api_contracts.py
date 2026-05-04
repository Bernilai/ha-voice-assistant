"""Stable JSON shapes for handoff / client contracts (keys only, not full snapshots)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _assert_keys(obj: dict, keys: set[str], *, label: str) -> None:
    missing = keys - obj.keys()
    extra = set(obj.keys()) - keys
    assert not missing, f"{label}: missing keys {missing}"
    assert not extra, f"{label}: unexpected extra keys {extra}"


def test_get_health_shape(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    _assert_keys(r.json(), {"status"}, label="GET /api/health")


def test_get_state_house_top_level_shape(client: TestClient) -> None:
    r = client.get("/api/state/house")
    assert r.status_code == 200
    body = r.json()
    _assert_keys(body, {"version", "rooms"}, label="GET /api/state/house")
    assert body["version"] == "p3-ha"
    assert isinstance(body["rooms"], list)


def test_get_events_list_shape(client: TestClient) -> None:
    r = client.get("/api/events", params={"limit": 5})
    assert r.status_code == 200
    body = r.json()
    _assert_keys(body, {"events", "order"}, label="GET /api/events")
    assert body["order"] == "newest_first"
    if body["events"]:
        ev0 = body["events"][0]
        _assert_keys(ev0, {"id", "timestamp", "type", "message", "metadata"}, label="event item")


def test_post_intents_interpret_shape(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post("/api/intents/interpret", json={"text": "включи свет на кухне"})
    assert r.status_code == 200
    _assert_keys(
        r.json(),
        {"raw_text", "normalized_text", "canonical_intent", "entities", "status", "clarification"},
        label="POST /api/intents/interpret",
    )


def test_post_intents_execute_success_shape(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post(
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
    _assert_keys(
        r.json(),
        {
            "status",
            "spoken_response",
            "ui_message",
            "affected_entities",
            "queried_entities",
            "trace",
            "error_code",
            "error_message",
            "clarification",
        },
        label="POST /api/intents/execute",
    )


def test_post_intents_clarify_error_shape_matches_execute(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post(
        "/api/intents/clarify",
        json={"session_id": "00000000-0000-0000-0000-000000000099", "reply": "x"},
    )
    assert r.status_code == 200
    _assert_keys(
        r.json(),
        {
            "status",
            "spoken_response",
            "ui_message",
            "affected_entities",
            "queried_entities",
            "trace",
            "error_code",
            "error_message",
            "clarification",
        },
        label="POST /api/intents/clarify",
    )


def test_post_demo_reset_shape(client: TestClient) -> None:
    r = client.post("/api/demo/reset")
    assert r.status_code == 200
    _assert_keys(
        r.json(),
        {
            "ok",
            "message",
            "event_log_cleared",
            "clarification_sessions_cleared",
            "baseline_strategy",
            "baseline_semantics",
            "reset_at",
        },
        label="POST /api/demo/reset",
    )


def test_get_demo_status_shape(client: TestClient) -> None:
    r = client.get("/api/demo/status")
    assert r.status_code == 200
    body = r.json()
    _assert_keys(
        body,
        {
            "mode",
            "mode_semantics",
            "last_reset_at",
            "last_reset_ok",
            "last_reset_baseline_strategy",
            "last_replay_at",
            "last_replay_summary",
            "replay_catalog",
            "reset_contract",
        },
        label="GET /api/demo/status",
    )
    assert isinstance(body["replay_catalog"], list)
    if body["replay_catalog"]:
        row = body["replay_catalog"][0]
        _assert_keys(row, {"id", "title", "steps", "deterministic", "notes"}, label="replay_catalog entry")


def test_post_demo_replay_shape(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post("/api/demo/replay", json={"scenario_id": "room_status_kitchen"})
    assert r.status_code == 200
    _assert_keys(
        r.json(),
        {
            "ok",
            "scenario_id",
            "steps_total",
            "steps_run",
            "stopped_early",
            "step_results",
            "detail",
            "completed_at",
        },
        label="POST /api/demo/replay",
    )


def test_post_demo_set_mode_shape(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post("/api/demo/set-mode", json={"mode": "static"})
    assert r.status_code == 200
    _assert_keys(r.json(), {"ok", "mode", "semantics"}, label="POST /api/demo/set-mode")


def test_get_voice_status_shape(client: TestClient) -> None:
    r = client.get("/api/voice/status")
    assert r.status_code == 200
    _assert_keys(
        r.json(),
        {
            "integration_kind",
            "bridge_enabled",
            "transcript_endpoint_available",
            "ha_assist_local_path",
            "transcript_bridge_path",
            "supported_transcript_phrases_ru",
            "intentionally_unsupported_via_transcript",
            "clarification_policy_ru",
        },
        label="GET /api/voice/status",
    )


def test_post_voice_transcript_shape(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post("/api/voice/transcript", json={"transcript": "абракадабра"})
    assert r.status_code == 200
    _assert_keys(
        r.json(),
        {
            "outcome",
            "execution_claimed",
            "transcript",
            "message_ru",
            "voice_path",
            "interpret",
            "policy_reason",
            "execute",
        },
        label="POST /api/voice/transcript",
    )
