from fastapi.testclient import TestClient


def test_demo_reset_clears_events_and_restores_ha_baseline(client: TestClient) -> None:
    """Execute updates mock HA; reset restores baseline via HA seam."""
    client.post("/api/intents/execute", json=_exec_kitchen_on())
    r = client.post("/api/demo/reset")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["event_log_cleared"] is True
    assert data["clarification_sessions_cleared"] is True
    assert data["baseline_strategy"] == "mock_reset_to_baseline"
    assert "reset_at" in data
    ev = client.get("/api/events", params={"limit": 10}).json()["events"]
    assert any(e["type"] == "demo_reset" for e in ev)
    assert _kitchen_main_state(client) == "off"


def test_demo_status_includes_catalog_and_reset_fields(client: TestClient) -> None:
    r = client.get("/api/demo/status")
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "simulator"
    assert "replay_catalog" in data
    ids = {x["id"] for x in data["replay_catalog"]}
    assert "lights_kitchen_cycle" in ids
    assert "reset_contract" in data and len(data["reset_contract"]) > 10


def test_demo_replay_default_scenario_runs_deterministic_steps(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post("/api/demo/replay")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["scenario_id"] == "lights_kitchen_cycle"
    assert data["steps_total"] == 3
    assert data["steps_run"] == 3
    assert data["stopped_early"] is False
    assert len(data["step_results"]) == 3
    assert all(s["status"] == "success" for s in data["step_results"])
    st = client.get("/api/demo/status").json()
    assert st["last_replay_summary"]["ok"] is True


def test_demo_replay_unknown_scenario_returns_ok_false(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post("/api/demo/replay", json={"scenario_id": "does_not_exist"})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False
    assert data["steps_run"] == 0


def test_demo_replay_unknown_scenario_does_not_overwrite_last_replay_summary(client: TestClient) -> None:
    """Unknown catalog id returns immediately; operator summary reflects last completed replay only."""
    client.post("/api/demo/reset")
    assert client.post("/api/demo/replay", json={"scenario_id": "room_status_kitchen"}).json()["ok"] is True
    summary_before = client.get("/api/demo/status").json()["last_replay_summary"]
    assert summary_before is not None
    assert summary_before["ok"] is True
    at_before = client.get("/api/demo/status").json()["last_replay_at"]

    bad = client.post("/api/demo/replay", json={"scenario_id": "not_in_catalog"}).json()
    assert bad["ok"] is False
    assert bad["completed_at"] is None

    st = client.get("/api/demo/status").json()
    assert st["last_replay_summary"] == summary_before
    assert st["last_replay_at"] == at_before


def test_demo_replay_stops_on_first_non_success_step(client: TestClient, monkeypatch) -> None:
    """Replay is sequential; first failing execute step yields partial step_results and demo_replay event."""
    from app.models.intents import IntentExecuteRequest
    from app.services.response_builder import ExecutionResponseBuilder

    client.post("/api/demo/reset")
    st = client.app.state.app_state
    real_execute = st.execution.execute
    call_n = {"n": 0}

    def wrapped(body: IntentExecuteRequest):
        call_n["n"] += 1
        if call_n["n"] == 2:
            return ExecutionResponseBuilder.error(
                spoken_response="ошибка",
                ui_message="симуляция сбоя",
                error_code="simulated_step_failure",
                error_message="injected for replay test",
                trace={"phase": "test_inject"},
            )
        return real_execute(body)

    monkeypatch.setattr(st.execution, "execute", wrapped)
    r = client.post("/api/demo/replay")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False
    assert data["stopped_early"] is True
    assert data["steps_run"] == 2
    assert data["steps_total"] == 3
    assert len(data["step_results"]) == 2
    assert data["step_results"][0]["status"] == "success"
    assert data["step_results"][1]["status"] == "error"
    assert data["step_results"][1]["error_code"] == "simulated_step_failure"
    assert "Stopped at step 1" in data["detail"]
    ev = client.get("/api/events", params={"limit": 30}).json()["events"]
    assert any(e["type"] == "demo_replay" and "stopped at step 1" in e["message"].lower() for e in ev)
    summ = client.get("/api/demo/status").json()["last_replay_summary"]
    assert summ is not None
    assert summ["ok"] is False
    assert summ["stopped_early"] is True


def test_demo_set_mode(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post("/api/demo/set-mode", json={"mode": "static"})
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "static"
    assert data["ok"] is True
    assert "semantics" in data and len(data["semantics"]) > 5


def test_demo_reset_ok_false_when_baseline_raises(client: TestClient, monkeypatch) -> None:
    import app.api.routes.demo as demo_routes

    def _boom(_c, _w):
        raise RuntimeError("HA unavailable")

    monkeypatch.setattr(demo_routes, "apply_demo_baseline", _boom)
    r = client.post("/api/demo/reset")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False
    assert data["event_log_cleared"] is False
    assert data["clarification_sessions_cleared"] is False
    assert "Baseline apply failed" in data["message"]


def test_demo_replay_room_status_scenario(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r = client.post("/api/demo/replay", json={"scenario_id": "room_status_kitchen"})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["scenario_id"] == "room_status_kitchen"
    assert data["step_results"][0]["intent"] == "get_room_status"


def _exec_kitchen_on() -> dict:
    return {
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
    }


def _kitchen_main_state(client: TestClient) -> str:
    house = client.get("/api/state/house").json()
    kitchen = next(x for x in house["rooms"] if x["room_id"] == "kitchen")
    main = next(d for d in kitchen["devices"] if d["entity_id"] == "light.kitchen_main")
    return main["state"]
