from fastapi.testclient import TestClient


def test_events_limit_bounds_and_newest_first_order(client: TestClient) -> None:
    client.post("/api/demo/reset")
    for _ in range(3):
        client.post("/api/intents/interpret", json={"text": "включи свет на кухне"})
    r = client.get("/api/events", params={"limit": 2})
    assert r.status_code == 200
    j = r.json()
    assert j["order"] == "newest_first"
    evs = j["events"]
    assert len(evs) == 2
    assert int(evs[0]["id"]) > int(evs[1]["id"])
    assert evs[0]["type"] == "intent_interpret"


def test_events_newest_first_and_reset(client: TestClient) -> None:
    client.post("/api/demo/reset")
    r0 = client.get("/api/events")
    assert r0.status_code == 200
    j0 = r0.json()
    assert j0["order"] == "newest_first"
    assert len(j0["events"]) >= 1
    client.post("/api/intents/interpret", json={"text": "включи свет на кухне"})
    r1 = client.get("/api/events")
    evs = r1.json()["events"]
    assert evs[0]["type"] == "intent_interpret"
