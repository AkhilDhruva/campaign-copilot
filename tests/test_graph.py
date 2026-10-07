"""End-to-end run of the workflow in mock mode, through the real MCP client and LangGraph."""

import pytest

from campaign_copilot.audit import AuditLog, verify
from campaign_copilot.runner import CampaignRunner

GOAL = "Grow checking deposits 10% at our Dallas branches this quarter"


@pytest.fixture(autouse=True)
def _env(db_path, monkeypatch):
    monkeypatch.setenv("NORTHWIND_DB", str(db_path))
    monkeypatch.setenv("MOCK_LLM", "1")


async def test_run_pauses_for_approval_then_publishes(tmp_path):
    events = []

    async def on_event(ev):
        events.append(ev)

    audit = AuditLog(tmp_path / "audit.jsonl")
    async with CampaignRunner(audit=audit) as runner:
        run_id = runner.new_run_id()
        state = await runner.start(run_id, GOAL, on_event)

        # Paused before publish, nothing shipped.
        assert state["next"] == ["publish"]
        assert state["status"] == "awaiting_approval"
        assert state["plan"]["product"] == "checking"
        assert state["audience"]["branch_ids"] == [1, 2, 3, 4]

        # First draft had deliberate problems; revision 1 is clean.
        assert state["revision"] == 1
        assert len(state["drafts"]) == 2
        assert state["compliance"]["passed"] is True
        assert state["issues_caught"] >= 2
        assert state["evaluation"]["decision"] == "accept"
        assert state["evaluation"]["score"] >= 80

        # Business impact is derived from the data, and labelled as an estimate.
        impact = state["impact"]
        assert impact["reach"] == state["audience"]["projected_reach"] > 0
        assert impact["projected_accounts"] > 0
        assert "Estimates only" in impact["basis"]

        # Data went through MCP tools.
        tools_used = {c["tool"] for c in state["tool_calls"]}
        assert {
            "resolve_branches",
            "branch_performance",
            "query_segments",
            "past_campaign_results",
        } <= tools_used

        steps = [e["step"] for e in events]
        assert steps[:3] == ["start", "planner", "audience"]
        assert steps.count("copy") == 2 and steps[-1] == "approval"

        final = await runner.decide(run_id, "approve", on_event)
        assert final["status"] == "published"
        assert final["next"] == []
        assert events[-1]["status"] == "published"

    chain = verify(audit.path)
    assert chain["ok"] and chain["records"] >= 9
    steps_logged = [r["step"] for r in audit.records(run_id)]
    assert steps_logged[0] == "start" and steps_logged[-1] == "publish"
    assert "human_decision" in steps_logged


async def test_reject_does_not_publish(tmp_path):
    async with CampaignRunner(audit=AuditLog(tmp_path / "a.jsonl")) as runner:
        run_id = runner.new_run_id()
        await runner.start(run_id, "Open 300 new high-yield savings accounts in Plano this quarter")
        final = await runner.decide(run_id, "reject")
        assert final["status"] == "rejected"
        assert final["plan"]["product"] == "savings"
        assert final["copy"]["offer_apy"] == 4.1
        assert final["compliance"]["passed"]


async def test_decide_before_pause_is_an_error(tmp_path):
    async with CampaignRunner(audit=AuditLog(tmp_path / "a.jsonl")) as runner:
        with pytest.raises(RuntimeError):
            await runner.decide("nope", "approve")


async def test_unknown_location_falls_back_to_all_branches(tmp_path):
    async with CampaignRunner(audit=AuditLog(tmp_path / "a.jsonl")) as runner:
        run_id = runner.new_run_id()
        state = await runner.start(run_id, "Win 50 mortgage refinances in Springfield by March")
        assert len(state["audience"]["branch_ids"]) == 12
        assert state["plan"]["product"] == "mortgage"
