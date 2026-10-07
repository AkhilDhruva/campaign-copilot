"""The Campaign Copilot workflow as a LangGraph state graph.

    planner -> audience -> copy -> compliance -> evaluator -+-> publish -> END
                             ^                              |
                             +------ revise (max 2) --------+

The graph is compiled with a checkpointer and `interrupt_before=["publish"]`, so a run always
pauses before the publish node. A human sets `decision` ("approve" or "reject") on the saved
state and resumes; nothing ships without that click.

`recursion_limit` is the hard ceiling on node executions, independent of the revision cap.
"""

from __future__ import annotations

import operator
from functools import partial
from typing import Annotated, Any, Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from campaign_copilot.agents import nodes
from campaign_copilot.agents.nodes import Runtime

MAX_STEPS = 25  # hard stop: 6 nodes + 2 revision loops of 3 nodes is 12; 25 leaves headroom


class CampaignState(TypedDict, total=False):
    run_id: str
    goal: str
    plan: dict[str, Any]
    audience: dict[str, Any]
    evidence: dict[str, Any]
    copy: dict[str, Any]
    drafts: list[dict[str, Any]]
    compliance: dict[str, Any]
    evaluation: dict[str, Any]
    feedback: list[str]
    revision: int
    issues_caught: int
    impact: dict[str, Any]
    status: str
    decision: str
    timeline: Annotated[list[dict[str, Any]], operator.add]


def route_after_evaluator(state: CampaignState) -> Literal["copy", "publish"]:
    return "copy" if state["evaluation"]["decision"] == "revise" else "publish"


def build_graph(rt: Runtime, checkpointer: Any | None = None):
    g = StateGraph(CampaignState)
    g.add_node("planner", partial(nodes.planner, rt=rt))
    g.add_node("audience", partial(nodes.audience, rt=rt))
    g.add_node("copy", partial(nodes.copywriter, rt=rt))
    g.add_node("compliance", partial(nodes.compliance, rt=rt))
    g.add_node("evaluator", partial(nodes.evaluator, rt=rt))
    g.add_node("publish", partial(nodes.publish, rt=rt))

    g.add_edge(START, "planner")
    g.add_edge("planner", "audience")
    g.add_edge("audience", "copy")
    g.add_edge("copy", "compliance")
    g.add_edge("compliance", "evaluator")
    g.add_conditional_edges(
        "evaluator", route_after_evaluator, {"copy": "copy", "publish": "publish"}
    )
    g.add_edge("publish", END)

    return g.compile(checkpointer=checkpointer or MemorySaver(), interrupt_before=["publish"])


def run_config(run_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": run_id}, "recursion_limit": MAX_STEPS}
