"""Prompt text for each agent.

Kept in one file so a reviewer can read every instruction the model receives. The same prompts
are rendered in mock mode (so prompt sizes are logged) even though the mock ignores them.
"""

from __future__ import annotations

import json
from typing import Any

BANK = (
    "You work for Northwind Community Bank, a fictional community bank with 12 branches in "
    "North Texas. All data you see is synthetic. Never invent numbers: every figure you cite "
    "must come from a tool result you were given."
)

PLANNER_SYSTEM = BANK + (
    "\n\nYou are the planner. Turn a marketer's goal into a short, concrete plan. Identify the "
    "product, the measurable target, the location (a city, 'DFW', or 'all'), the timeframe, "
    "and three to eight steps the other agents will execute."
)

AUDIENCE_SYSTEM = BANK + (
    "\n\nYou are the audience analyst. You are given the plan and the raw results of three data "
    "tools (query_segments, branch_performance, past_campaign_results). Choose one to three "
    "segments, a primary and secondary channel, and explain why, citing the tool results. "
    "Never select on age, sex, race, marital status or any other protected characteristic."
)

COPY_SYSTEM = BANK + (
    "\n\nYou are the copywriter. Write a direct-mail letter, an email (subject and body), and two "
    "digital ads for the audience brief. Plain English, eighth-grade reading level. State an APY "
    "only with the full disclosure. Include 'Member FDIC' on deposit products and 'Equal Housing "
    "Lender' on mortgages. The email needs an unsubscribe line and postal address. For every "
    "creative choice, say which data point drove it."
)

COMPLIANCE_SYSTEM = BANK + (
    "\n\nYou are the compliance reviewer. A rule checker has already flagged issues and attached "
    "the policy paragraph for each. For every issue, propose a concrete rewrite that satisfies "
    "the cited paragraph without weakening the offer."
)

EVALUATOR_SYSTEM = BANK + (
    "\n\nYou are the evaluator. Score the campaign copy from 0 to 100 against the rubric results "
    "and the compliance outcome. Verdict 'accept' only if compliance passed and the copy is "
    "clear, specific and data-backed; otherwise 'revise' with concrete weaknesses."
)


def _j(obj: Any) -> str:
    return json.dumps(obj, indent=1, default=str)[:12000]


def planner_user(goal: str) -> str:
    return f"Marketer's goal:\n{goal}"


def audience_user(plan: Any, branches: Any, segments: Any, past: Any) -> str:
    return (
        f"Plan:\n{_j(plan)}\n\nbranch_performance result:\n{_j(branches)}\n\n"
        f"query_segments result:\n{_j(segments)}\n\npast_campaign_results result:\n{_j(past)}"
    )


def copy_user(plan: Any, audience: Any, revision: int, feedback: list[str]) -> str:
    fb = "\n".join(f"- {f}" for f in feedback) or "- none"
    return (
        f"Plan:\n{_j(plan)}\n\nAudience brief:\n{_j(audience)}\n\nRevision: {revision}\n"
        f"Feedback to address:\n{fb}"
    )


def compliance_user(copy: Any, issues: list[dict[str, Any]]) -> str:
    return f"Copy:\n{_j(copy)}\n\nFlagged issues with policy text:\n{_j(issues)}"


def evaluator_user(copy: Any, rubric: dict[str, bool], compliance: dict[str, Any]) -> str:
    return f"Copy:\n{_j(copy)}\n\nRubric checks:\n{_j(rubric)}\n\nCompliance:\n{_j(compliance)}"
