"""The MCP server is exercised through a real MCP client, in-process (no subprocess, no network)."""

import pytest
from mcp import Client

from campaign_copilot.mcp_server.server import mcp

EXPECTED_TOOLS = {
    "resolve_branches",
    "query_segments",
    "branch_performance",
    "past_campaign_results",
}


@pytest.fixture(autouse=True)
def _point_server_at_test_db(db_path, monkeypatch):
    monkeypatch.setenv("NORTHWIND_DB", str(db_path))


async def test_lists_the_four_tools():
    async with Client(mcp) as client:
        tools = await client.list_tools()
    names = {t.name for t in tools.tools}
    assert names == EXPECTED_TOOLS
    # Every tool has a description the model can read.
    assert all(t.description for t in tools.tools)


async def test_resolve_then_query_round_trip():
    async with Client(mcp) as client:
        branches = await client.call_tool("resolve_branches", {"location": "Dallas"})
        ids = [b["branch_id"] for b in branches.structured_content["result"]]
        assert ids == [1, 2, 3, 4]

        seg = await client.call_tool(
            "query_segments",
            {"branch_ids": ids, "product_gap": "checking", "channel": "direct_mail"},
        )
        data = seg.structured_content
        assert data["customers"] > 0
        assert data["direct_mail_opt_in_rate"] == 1.0

        perf = await client.call_tool("branch_performance", {"branch_ids": ids})
        assert len(perf.structured_content["result"]) == 4

        past = await client.call_tool(
            "past_campaign_results", {"product": "checking", "channel": "direct_mail"}
        )
        assert past.structured_content["campaign_count"] > 0
        assert past.structured_content["by_channel"][0]["channel"] == "direct_mail"


async def test_bad_input_is_an_error_not_a_crash():
    async with Client(mcp) as client:
        result = await client.call_tool("query_segments", {"product_gap": "crypto"})
    assert result.is_error
