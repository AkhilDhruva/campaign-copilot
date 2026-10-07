"""Northwind data MCP server.

Exposes the read-only query functions as MCP tools so the agents (and any MCP client such as
Claude Desktop or the MCP Inspector) can ask the bank's data questions through a standard
protocol instead of raw SQL.

Run it on stdio (what the LangGraph workflow uses):

    python -m campaign_copilot.mcp_server.server

Or inspect it interactively:

    mcp dev campaign_copilot/mcp_server/server.py

MCP SDK 2.x note: the server class is `MCPServer` (it was called `FastMCP` in 1.x).
"""

from __future__ import annotations

from typing import Any

from mcp.server import MCPServer

from campaign_copilot.data import queries

mcp = MCPServer(
    "northwind-data",
    instructions=(
        "Read-only access to Northwind Community Bank's synthetic customer, branch and "
        "campaign data. Use resolve_branches first to turn a place name into branch ids."
    ),
)


@mcp.tool()
def resolve_branches(
    location: str | None = None, branch_ids: list[int] | None = None
) -> list[dict[str, Any]]:
    """Map a place name ("Dallas", "DFW", "Frisco") or explicit ids to branch records.

    Call with no arguments to list all 12 branches.
    """
    return queries.resolve_branches(location=location, branch_ids=branch_ids)


@mcp.tool()
def query_segments(
    branch_ids: list[int] | None = None,
    segment: str | None = None,
    product_gap: str | None = None,
    min_engagement: float | None = None,
    channel: str | None = None,
) -> dict[str, Any]:
    """Count and profile customers matching filters, with a per-segment breakdown.

    product_gap: customers who do NOT yet hold this product (checking, savings, credit_card,
    mortgage, auto_loan). channel: keep only customers opted in to direct_mail or email.
    Segments: young_professional, family, retiree, small_business, student.
    """
    return queries.query_segments(
        branch_ids=branch_ids,
        segment=segment,
        product_gap=product_gap,
        min_engagement=min_engagement,
        channel=channel,
    )


@mcp.tool()
def branch_performance(branch_ids: list[int] | None = None) -> list[dict[str, Any]]:
    """Deposits, checking penetration, engagement and campaign history per branch."""
    return queries.branch_performance(branch_ids=branch_ids)


@mcp.tool()
def past_campaign_results(
    product: str | None = None,
    channel: str | None = None,
    branch_ids: list[int] | None = None,
    segment: str | None = None,
) -> dict[str, Any]:
    """Past campaigns matching the filters plus per-channel response rate, conversion and
    cost per acquired account. Bank-wide campaigns are included when filtering by branch."""
    return queries.past_campaign_results(
        product=product, channel=channel, branch_ids=branch_ids, segment=segment
    )


if __name__ == "__main__":
    mcp.run()
