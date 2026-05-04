from fastapi.testclient import TestClient


def test_interpret_known_kitchen_light(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post("/api/intents/interpret", json={"text": "  включи свет на кухне  "})
    assert r.status_code == 200
    b = r.json()
    assert b["status"] == "success"
    assert b["canonical_intent"] == "turn_on_device"
    assert b["entities"]["room"] == "kitchen"


def test_interpret_target_ru_phrases_coverage(client: TestClient) -> None:
    client.post("/api/demo/reset")
    cases = [
        (
            "включи свет в гостиной",
            "turn_on_device",
            {"room": "living_room", "device_type": "light", "target_entity_id": "light.living_room_main"},
        ),
        (
            "выключи свет в гостиной",
            "turn_off_device",
            {"room": "living_room", "device_type": "light", "target_entity_id": "light.living_room_main"},
        ),
        (
            "включи свет в спальне",
            "turn_on_device",
            {"room": "bedroom", "device_type": "light", "target_entity_id": "light.bedroom_main"},
        ),
        (
            "выключи свет в спальне",
            "turn_off_device",
            {"room": "bedroom", "device_type": "light", "target_entity_id": "light.bedroom_main"},
        ),
        (
            "открой шторы в гостиной",
            "turn_on_device",
            {
                "room": "living_room",
                "device_type": "curtains",
                "target_entity_id": "cover.living_room_curtains",
            },
        ),
        (
            "закрой шторы в гостиной",
            "turn_off_device",
            {
                "room": "living_room",
                "device_type": "curtains",
                "target_entity_id": "cover.living_room_curtains",
            },
        ),
        (
            "открой шторы в спальне",
            "turn_on_device",
            {"room": "bedroom", "device_type": "curtains", "target_entity_id": "cover.bedroom_curtains"},
        ),
        (
            "закрой шторы в спальне",
            "turn_off_device",
            {"room": "bedroom", "device_type": "curtains", "target_entity_id": "cover.bedroom_curtains"},
        ),
        (
            "включи чайник",
            "turn_on_device",
            {"room": "kitchen", "device_type": "kettle", "target_entity_id": "switch.kitchen_kettle"},
        ),
        (
            "выключи чайник",
            "turn_off_device",
            {"room": "kitchen", "device_type": "kettle", "target_entity_id": "switch.kitchen_kettle"},
        ),
        (
            "включи обогреватель в спальне",
            "turn_on_device",
            {"room": "bedroom", "device_type": "heater", "target_entity_id": "switch.bedroom_heater"},
        ),
        (
            "выключи обогреватель в спальне",
            "turn_off_device",
            {"room": "bedroom", "device_type": "heater", "target_entity_id": "switch.bedroom_heater"},
        ),
        (
            "какая температура в спальне",
            "get_sensor_status",
            {"room": "bedroom", "sensor_kind": "temperature"},
        ),
        (
            "какая температура на кухне",
            "get_sensor_status",
            {"room": "kitchen", "sensor_kind": "temperature"},
        ),
        (
            "какая температура в гостиной",
            "get_sensor_status",
            {"room": "living_room", "sensor_kind": "temperature"},
        ),
    ]
    for phrase, intent, entities in cases:
        r = client.post("/api/intents/interpret", json={"text": phrase})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "success"
        assert body["canonical_intent"] == intent
        assert body["entities"] == entities


def test_interpret_ambiguous(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post("/api/intents/interpret", json={"text": "выключи свет"})
    assert r.status_code == 200
    b = r.json()
    assert b["status"] == "clarification_required"
    assert b["clarification"]["reason"] == "missing_room"


def test_interpret_unsupported(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post("/api/intents/interpret", json={"text": "абракадабра тест"})
    assert r.status_code == 200
    assert r.json()["status"] == "unsupported"


def test_interpret_kitchen_room_status_phrase(client: TestClient) -> None:
    client.post("/api/demo/reset")
    for phrase in ("статус кухни", "что на кухне"):
        r = client.post("/api/intents/interpret", json={"text": phrase})
        assert r.status_code == 200
        b = r.json()
        assert b["status"] == "success"
        assert b["canonical_intent"] == "get_room_status"
        assert b["entities"]["room"] == "kitchen"


def test_clarify_unknown_session_returns_error(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post(
        "/api/intents/clarify",
        json={"session_id": "00000000-0000-0000-0000-000000000099", "reply": "kitchen"},
    )
    assert r.status_code == 200
    b = r.json()
    assert b["status"] == "error"
    assert b["error_code"] == "clarification_session_invalid"


def test_execute_unsupported_intent_stable_error_contract(client: TestClient) -> None:
    client.post("/api/demo/reset")
    body = {
        "intent": "unknown_intent_p1_test",
        "source": "text",
        "utterance": "probe",
        "entities": {},
        "confidence": 1.0,
        "requires_clarification": False,
        "meta": {},
    }
    r = client.post("/api/intents/execute", json=body)
    assert r.status_code == 200
    out = r.json()
    assert out["status"] == "error"
    assert out["error_code"] == "unsupported_intent"
    assert out["trace"]["intent"] == "unknown_intent_p1_test"
    assert out["trace"]["execution_engine"] == "p4a-ha"
    assert out["affected_entities"] == []


def test_execute_kitchen_light_on_updates_ha_backed_state(client: TestClient) -> None:
    client.post("/api/demo/reset")
    body = {
        "intent": "turn_on_device",
        "source": "text",
        "utterance": "включи свет на кухне",
        "entities": {
            "room": "kitchen",
            "device_type": "light",
            "target_entity_id": "light.kitchen_main",
        },
        "confidence": 1.0,
        "requires_clarification": False,
        "meta": {"language": "ru", "session_id": "t-1"},
    }
    r = client.post("/api/intents/execute", json=body)
    assert r.status_code == 200
    out = r.json()
    assert out["status"] == "success"
    assert "light.kitchen_main" in out["affected_entities"]
    assert out["queried_entities"] == []
    house = client.get("/api/state/house").json()
    kitchen = next(x for x in house["rooms"] if x["room_id"] == "kitchen")
    main = next(d for d in kitchen["devices"] if d["entity_id"] == "light.kitchen_main")
    assert main["state"] == "on"
