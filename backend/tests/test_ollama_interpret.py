"""Tests for Ollama NLU fallback validation and HTTP parsing."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from app.services import ollama_interpret as oi


def test_parse_ollama_timeout_none_uses_default() -> None:
    assert oi._parse_ollama_timeout_seconds(None) == oi._DEFAULT_OLLAMA_TIMEOUT_SEC


def test_parse_ollama_timeout_empty_or_whitespace_uses_default() -> None:
    assert oi._parse_ollama_timeout_seconds("") == oi._DEFAULT_OLLAMA_TIMEOUT_SEC
    assert oi._parse_ollama_timeout_seconds("   ") == oi._DEFAULT_OLLAMA_TIMEOUT_SEC


def test_parse_ollama_timeout_accepts_numeric_strings() -> None:
    assert oi._parse_ollama_timeout_seconds("30") == 30.0
    assert oi._parse_ollama_timeout_seconds("  2.5  ") == 2.5


def test_parse_ollama_timeout_invalid_string_falls_back(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    assert oi._parse_ollama_timeout_seconds("invalid") == oi._DEFAULT_OLLAMA_TIMEOUT_SEC
    assert "Invalid OLLAMA_TIMEOUT" in caplog.text


def _valid_turn_on_entities() -> dict:
    return {
        "room": "kitchen",
        "device_type": "light",
        "target_entity_id": "light.kitchen_main",
    }


def test_validate_accepts_turn_on_with_device_type() -> None:
    out = oi._validate({"intent": "turn_on_device", "entities": _valid_turn_on_entities()})
    assert out is not None
    assert out.canonical_intent == "turn_on_device"
    assert out.entities["device_type"] == "light"


def test_validate_rejects_turn_on_missing_device_type() -> None:
    e = _valid_turn_on_entities()
    del e["device_type"]
    assert oi._validate({"intent": "turn_on_device", "entities": e}) is None


def test_validate_rejects_turn_on_invalid_device_type() -> None:
    e = {**_valid_turn_on_entities(), "device_type": "fan"}
    assert oi._validate({"intent": "turn_on_device", "entities": e}) is None


def test_validate_accepts_get_sensor_status_with_sensor_kind() -> None:
    out = oi._validate({
        "intent": "get_sensor_status",
        "entities": {"room": "kitchen", "sensor_kind": "temperature"},
    })
    assert out is not None
    assert out.entities["sensor_kind"] == "temperature"


def test_validate_rejects_get_sensor_status_missing_sensor_kind() -> None:
    assert oi._validate({
        "intent": "get_sensor_status",
        "entities": {"room": "kitchen"},
    }) is None


def test_validate_rejects_get_sensor_status_invalid_sensor_kind() -> None:
    assert oi._validate({
        "intent": "get_sensor_status",
        "entities": {"room": "kitchen", "sensor_kind": "pressure"},
    }) is None


def test_validate_accepts_living_room_motion_and_kitchen_window() -> None:
    m = oi._validate({
        "intent": "get_sensor_status",
        "entities": {"room": "living_room", "sensor_kind": "motion"},
    })
    assert m is not None and m.entities["sensor_kind"] == "motion"
    w = oi._validate({
        "intent": "get_sensor_status",
        "entities": {"room": "kitchen", "sensor_kind": "window"},
    })
    assert w is not None and w.entities["sensor_kind"] == "window"


def test_validate_rejects_sensor_pair_not_in_p4b_matrix() -> None:
    # motion exists only for living_room in status_resolver
    assert oi._validate({
        "intent": "get_sensor_status",
        "entities": {"room": "kitchen", "sensor_kind": "motion"},
    }) is None


def test_validate_rejects_non_dict_entities() -> None:
    assert oi._validate({"intent": "turn_on_device", "entities": []}) is None
    assert oi._validate({"intent": "get_room_status", "entities": ["room", "kitchen"]}) is None


def test_validate_rejects_unknown_intent_string() -> None:
    assert oi._validate({"intent": "dim_lights", "entities": {}}) is None


def test_validate_rejects_null_intent() -> None:
    assert oi._validate({"intent": None, "entities": {}}) is None


def test_ollama_interpret_returns_unsupported_when_call_returns_none() -> None:
    with patch.object(oi, "_call_ollama", return_value=None):
        r = oi.ollama_interpret("что-нибудь на русском")
    assert r.status == "unsupported"
    assert r.canonical_intent is None
    assert r.raw_text == "что-нибудь на русском"


def test_ollama_interpret_sets_raw_text_on_success() -> None:
    parsed = {
        "intent": "get_room_status",
        "entities": {"room": "bedroom"},
    }
    with patch.object(oi, "_call_ollama", return_value=parsed):
        r = oi.ollama_interpret("что в спальне")
    assert r.status == "success"
    assert r.canonical_intent == "get_room_status"
    assert r.raw_text == "что в спальне"
    assert r.normalized_text == "что в спальне"


def test_ollama_interpret_returns_unsupported_when_validation_fails() -> None:
    with patch.object(oi, "_call_ollama", return_value={"intent": "turn_on_device", "entities": {}}):
        r = oi.ollama_interpret("включи всё")
    assert r.status == "unsupported"


def test_call_ollama_parses_json_wrapped_in_markdown_fences() -> None:
    inner = '{"intent": "get_room_status", "entities": {"room": "kitchen"}}'
    fenced = f"```json\n{inner}\n```"
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": fenced}
    mock_resp.raise_for_status = MagicMock()
    with patch("app.services.ollama_interpret.httpx.post", return_value=mock_resp) as post:
        out = oi._call_ollama("статус кухни")
    post.assert_called_once()
    assert out == {"intent": "get_room_status", "entities": {"room": "kitchen"}}


def test_call_ollama_strips_uppercase_language_fence() -> None:
    inner = '{"intent": "get_room_status", "entities": {"room": "kitchen"}}'
    fenced = f"```JSON\n{inner}\n```"
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": fenced}
    mock_resp.raise_for_status = MagicMock()
    with patch("app.services.ollama_interpret.httpx.post", return_value=mock_resp):
        out = oi._call_ollama("статус кухни")
    assert out == {"intent": "get_room_status", "entities": {"room": "kitchen"}}


def test_call_ollama_returns_none_on_json_decode_error() -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "not json {"}
    mock_resp.raise_for_status = MagicMock()
    with patch("app.services.ollama_interpret.httpx.post", return_value=mock_resp):
        assert oi._call_ollama("x") is None


def test_call_ollama_returns_none_on_http_error() -> None:
    import httpx

    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "bad", request=MagicMock(), response=MagicMock(),
    )
    with patch("app.services.ollama_interpret.httpx.post", return_value=mock_resp):
        assert oi._call_ollama("x") is None
