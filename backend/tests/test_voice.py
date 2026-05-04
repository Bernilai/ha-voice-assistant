"""P9 optional voice transcript bridge — deterministic, no microphone."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.models.intents import IntentInterpretResponse


def test_voice_status_shape(client: TestClient) -> None:
    r = client.get("/api/voice/status")
    assert r.status_code == 200
    b = r.json()
    assert set(b.keys()) == {
        "integration_kind",
        "bridge_enabled",
        "transcript_endpoint_available",
        "ha_assist_local_path",
        "transcript_bridge_path",
        "supported_transcript_phrases_ru",
        "intentionally_unsupported_via_transcript",
        "clarification_policy_ru",
    }
    assert b["integration_kind"] == "ha_assist_plus_transcript_bridge"
    assert b["bridge_enabled"] is True
    assert b["transcript_endpoint_available"] is True


def test_voice_transcript_kitchen_on_executed(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post("/api/voice/transcript", json={"transcript": "включи свет на кухне"})
    assert r.status_code == 200
    b = r.json()
    assert b["outcome"] == "executed"
    assert b["execution_claimed"] is True
    assert b["voice_path"] == "transcript_bridge"
    assert b["execute"] is not None
    assert b["execute"]["status"] == "success"
    assert b["interpret"]["canonical_intent"] == "turn_on_device"
    assert b["interpret"]["entities"]["target_entity_id"] == "light.kitchen_main"


def test_voice_transcript_interpret_clarification_fallback(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post("/api/voice/transcript", json={"transcript": "выключи свет"})
    assert r.status_code == 200
    b = r.json()
    assert b["outcome"] == "fallback_to_text"
    assert b["execution_claimed"] is False
    assert b["policy_reason"] == "interpret_clarification_not_supported_via_voice"
    assert b["interpret"]["status"] == "clarification_required"
    assert b["execute"] is None


def test_voice_transcript_unsupported_interpret_fallback(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post("/api/voice/transcript", json={"transcript": "абракадабра"})
    assert r.status_code == 200
    b = r.json()
    assert b["outcome"] == "fallback_to_text"
    assert b["policy_reason"] == "interpret_unsupported"


def test_voice_transcript_room_status_executed(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post("/api/voice/transcript", json={"transcript": "статус кухни"})
    assert r.status_code == 200
    b = r.json()
    assert b["outcome"] == "executed"
    assert b["execute"]["status"] == "success"
    assert b["execute"]["trace"]["intent"] == "get_room_status"


def test_voice_bridge_disabled_returns_bridge_disabled(client: TestClient) -> None:
    client.post("/api/demo/reset")
    client.app.state.app_state.voice_bridge_enabled = False
    r = client.post("/api/voice/transcript", json={"transcript": "включи свет на кухне"})
    assert r.status_code == 200
    b = r.json()
    assert b["outcome"] == "bridge_disabled"
    assert b["execution_claimed"] is False
    assert b["policy_reason"] == "bridge_disabled"


def test_voice_execute_clarification_fallback_with_monkeypatch(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    """Defensive branch: if policy ever allowed ambiguous light, voice path must not claim execution."""
    client.post("/api/demo/reset")

    def fake_interpret(_text: str) -> IntentInterpretResponse:
        return IntentInterpretResponse(
            raw_text="forced",
            normalized_text="forced",
            canonical_intent="turn_on_device",
            entities={"room": "kitchen", "device_type": "light"},
            status="success",
            clarification=None,
        )

    monkeypatch.setattr("app.api.routes.voice.voice_subset_policy_reason", lambda _interp: None)
    monkeypatch.setattr("app.api.routes.voice.interpret_text", fake_interpret)

    r = client.post("/api/voice/transcript", json={"transcript": "forced"})
    assert r.status_code == 200
    b = r.json()
    assert b["outcome"] == "fallback_to_text"
    assert b["execution_claimed"] is False
    assert b["policy_reason"] == "execute_clarification_not_supported_via_voice"
    assert b["execute"] is not None
    assert b["execute"]["status"] == "clarification_required"
