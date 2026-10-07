"""The HTTP API, exercised with Starlette's TestClient (runs the lifespan and background tasks)."""

import json
import time

import pytest
from fastapi.testclient import TestClient

GOAL = "Grow checking deposits 10% at our Dallas branches this quarter"


@pytest.fixture
def client(db_path, tmp_path, monkeypatch):
    monkeypatch.setenv("NORTHWIND_DB", str(db_path))
    monkeypatch.setenv("AUDIT_LOG", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("MOCK_LLM", "1")
    from campaign_copilot.api.main import app

    with TestClient(app) as c:
        yield c


def _wait_for_pause(client: TestClient, run_id: str, timeout: float = 20) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = client.get(f"/api/runs/{run_id}").json()
        if state.get("status") in ("awaiting_approval", "published", "rejected") or state.get(
            "error"
        ):
            return state
        time.sleep(0.1)
    raise AssertionError("run did not pause in time")


def test_health(client):
    body = client.get("/api/health").json()
    assert body["ok"] and body["mock_llm"] is True and body["llm_backend"] == "mock"


def test_full_run_over_http(client):
    run_id = client.post("/api/runs", json={"goal": GOAL}).json()["run_id"]
    state = _wait_for_pause(client, run_id)
    assert state["error"] is None
    assert state["status"] == "awaiting_approval"
    assert state["compliance"]["passed"]
    assert state["impact"]["projected_accounts"] > 0

    # SSE replay ends at the terminal "waiting" event.
    with client.stream("GET", f"/api/runs/{run_id}/events") as resp:
        assert resp.headers["content-type"].startswith("text/event-stream")
        events = [json.loads(line[6:]) for line in resp.iter_lines() if line.startswith("data: ")]
    assert events[0]["step"] == "start" and events[-1]["status"] == "waiting"
    assert [e["step"] for e in events].count("copy") == 2

    decided = client.post(f"/api/runs/{run_id}/decision", json={"decision": "approve"}).json()
    assert decided["status"] == "published"

    audit = client.get(f"/api/audit/{run_id}").json()
    assert audit[-1]["step"] == "publish"
    assert client.get("/api/audit/verify").json()["ok"]


def test_reject_and_errors(client):
    assert client.get("/api/runs/nope").status_code == 404
    assert client.post("/api/runs", json={"goal": "short"}).status_code == 422
    assert client.post("/api/runs/nope/decision", json={"decision": "approve"}).status_code == 404

    run_id = client.post(
        "/api/runs", json={"goal": "Open 300 new savings accounts in Plano this quarter"}
    ).json()["run_id"]
    _wait_for_pause(client, run_id)
    assert (
        client.post(f"/api/runs/{run_id}/decision", json={"decision": "maybe"}).status_code == 422
    )
    assert (
        client.post(f"/api/runs/{run_id}/decision", json={"decision": "reject"}).json()["status"]
        == "rejected"
    )
    # Deciding twice is a conflict, not a crash.
    assert (
        client.post(f"/api/runs/{run_id}/decision", json={"decision": "approve"}).status_code == 409
    )


def test_policies_endpoint(client):
    rows = client.get("/api/policies").json()
    assert {"1.1", "2.2", "4.1"} <= {r["id"] for r in rows}
