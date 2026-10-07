"""The LangGraph nodes. Each one reads state, does one job, and returns the fields it changed.

Every node also:
  * appends a timeline event (what the UI shows live), and
  * writes an audit record (inputs, outputs, tool calls, timing) to the hash-chained log.

Nodes receive their collaborators (`llm`, `tools`, `audit`, `policy_index`) through a
`Runtime` object so tests can swap any of them.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from campaign_copilot.agents import prompts
from campaign_copilot.agents.schemas import (
    AudienceBrief,
    ComplianceFixes,
    CopyDraft,
    Evaluation,
    Plan,
)
from campaign_copilot.audit import AuditLog
from campaign_copilot.compliance.retrieval import PolicyIndex
from campaign_copilot.compliance.rules import check
from campaign_copilot.llm import LLM
from campaign_copilot.tools import DataTools

MAX_REVISIONS = 2  # the copy agent gets at most two more tries after the first draft


@dataclass
class Runtime:
    llm: LLM
    tools: DataTools
    audit: AuditLog
    policy_index: PolicyIndex


def _event(step: str, status: str, summary: str, started: float, **extra: Any) -> dict[str, Any]:
    return {
        "step": step,
        "status": status,
        "summary": summary,
        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
        "ts": time.time(),
        **extra,
    }


def _tool_calls_since(rt: Runtime, mark: int) -> list[dict[str, Any]]:
    return rt.tools.calls[mark:]


# ---------------------------------------------------------------- planner


async def planner(state: dict[str, Any], rt: Runtime) -> dict[str, Any]:
    started = time.perf_counter()
    goal = state["goal"]
    plan = rt.llm.structured(
        "planner", prompts.PLANNER_SYSTEM, prompts.planner_user(goal), Plan, {"goal": goal}
    )
    ev = _event(
        "planner", "done", f"{plan.product} · {plan.target_metric} · {plan.location}", started
    )
    rt.audit.append(
        state["run_id"],
        "planner",
        inputs={"goal": goal},
        outputs=plan.model_dump(),
        duration_ms=ev["duration_ms"],
    )
    return {"plan": plan.model_dump(), "timeline": [ev]}


# ---------------------------------------------------------------- audience


async def audience(state: dict[str, Any], rt: Runtime) -> dict[str, Any]:
    started = time.perf_counter()
    plan = Plan(**state["plan"])
    mark = len(rt.tools.calls)

    location = None if plan.location.lower() == "all" else plan.location
    branches = await rt.tools.call("resolve_branches", location=location)
    if not branches:  # unknown place name: fall back to every branch
        branches = await rt.tools.call("resolve_branches")
    branch_ids = [b["branch_id"] for b in branches]

    perf = await rt.tools.call("branch_performance", branch_ids=branch_ids)
    segments = await rt.tools.call(
        "query_segments", branch_ids=branch_ids, product_gap=plan.product
    )
    past = await rt.tools.call("past_campaign_results", product=plan.product)
    if past["campaign_count"] == 0:  # no history for this product: use all campaigns
        past = await rt.tools.call("past_campaign_results")

    brief = rt.llm.structured(
        "audience",
        prompts.AUDIENCE_SYSTEM,
        prompts.audience_user(plan.model_dump(), perf, segments, past),
        AudienceBrief,
        {"plan": plan, "branch_ids": branch_ids, "segments": segments, "past": past},
    )
    tool_calls = _tool_calls_since(rt, mark)
    ev = _event(
        "audience",
        "done",
        f"{brief.projected_reach:,} reachable customers in {len(brief.segments)} segments · "
        f"{brief.primary_channel.replace('_', ' ')} first",
        started,
        tool_calls=tool_calls,
    )
    rt.audit.append(
        state["run_id"],
        "audience",
        inputs={"plan": plan.model_dump()},
        outputs=brief.model_dump(),
        tool_calls=tool_calls,
        duration_ms=ev["duration_ms"],
    )
    return {
        "audience": brief.model_dump(),
        "evidence": {"branches": perf, "segments": segments, "past": past},
        "timeline": [ev],
    }


# ---------------------------------------------------------------- copy


async def copywriter(state: dict[str, Any], rt: Runtime) -> dict[str, Any]:
    started = time.perf_counter()
    plan = Plan(**state["plan"])
    brief = AudienceBrief(**state["audience"])
    revision = state.get("revision", 0)
    feedback = state.get("feedback", [])
    draft = rt.llm.structured(
        "copy",
        prompts.COPY_SYSTEM,
        prompts.copy_user(plan.model_dump(), brief.model_dump(), revision, feedback),
        CopyDraft,
        {"plan": plan, "audience": brief, "revision": revision, "feedback": feedback},
    )
    label = "first draft" if revision == 0 else f"revision {revision}"
    ev = _event(
        "copy",
        "done",
        f"{label}: letter, email, 2 ads · {len(draft.data_citations)} data citations",
        started,
    )
    rt.audit.append(
        state["run_id"],
        "copy",
        inputs={"revision": revision, "feedback": feedback},
        outputs=draft.model_dump(),
        duration_ms=ev["duration_ms"],
    )
    drafts = state.get("drafts", []) + [draft.model_dump()]
    return {"copy": draft.model_dump(), "drafts": drafts, "timeline": [ev]}


# ---------------------------------------------------------------- compliance


async def compliance(state: dict[str, Any], rt: Runtime) -> dict[str, Any]:
    started = time.perf_counter()
    draft = CopyDraft(**state["copy"])
    product = state["plan"]["product"]
    report = check(draft, product, rt.policy_index)
    issues = [i.to_dict() for i in report.issues]
    if issues:
        fixes = rt.llm.structured(
            "compliance",
            prompts.COMPLIANCE_SYSTEM,
            prompts.compliance_user(draft.model_dump(), issues),
            ComplianceFixes,
            {"issues": issues},
        )
        by_id = {f.issue_id: f.suggestion for f in fixes.fixes}
        for issue in issues:
            issue["fix"] = by_id.get(issue["id"])
    result = {"passed": report.passed, "issues": issues, "checked_rules": report.checked_rules}
    blocking = sum(1 for i in issues if i["severity"] == "block")
    ev = _event(
        "compliance",
        "passed" if report.passed else "failed",
        "no issues" if not issues else f"{len(issues)} issue(s), {blocking} blocking",
        started,
    )
    rt.audit.append(
        state["run_id"],
        "compliance",
        inputs={"rules": report.checked_rules},
        outputs=result,
        duration_ms=ev["duration_ms"],
    )
    total_caught = state.get("issues_caught", 0) + len(issues)
    return {"compliance": result, "issues_caught": total_caught, "timeline": [ev]}


# ---------------------------------------------------------------- evaluator


def rubric(draft: CopyDraft, brief: AudienceBrief) -> dict[str, bool]:
    """Objective checks a reviewer could tick off by hand."""
    text = " ".join([draft.letter, draft.email_body, *(a.body for a in draft.ads)])
    return {
        "cites_data": len(draft.data_citations) >= 2,
        "has_call_to_action": any(
            w in text.lower() for w in ("open", "visit", "apply", "call", "stop by")
        ),
        "names_the_bank": "northwind" in text.lower(),
        "mentions_offer": draft.offer_name.lower() in text.lower() or bool(draft.offer_apy),
        "letter_length_ok": 300 <= len(draft.letter) <= 1800,
        "email_subject_short": len(draft.email_subject) <= 80,
        "ads_distinct": draft.ads[0].headline != draft.ads[1].headline,
        "audience_matches_channel": brief.primary_channel in ("direct_mail", "email", "digital_ad"),
    }


async def evaluator(state: dict[str, Any], rt: Runtime) -> dict[str, Any]:
    started = time.perf_counter()
    draft = CopyDraft(**state["copy"])
    brief = AudienceBrief(**state["audience"])
    comp = state["compliance"]
    checks = rubric(draft, brief)
    evaluation = rt.llm.structured(
        "evaluator",
        prompts.EVALUATOR_SYSTEM,
        prompts.evaluator_user(draft.model_dump(), checks, comp),
        Evaluation,
        {"rubric": checks, "compliance_passed": comp["passed"]},
    )
    revision = state.get("revision", 0)
    feedback = [f"[{i['id']}] {i['message']} Fix: {i.get('fix') or ''}" for i in comp["issues"]]
    feedback += [f"Rubric miss: {k.replace('_', ' ')}" for k, v in checks.items() if not v]

    if evaluation.verdict == "accept":
        decision, status = "accept", "accepted"
    elif revision < MAX_REVISIONS:
        decision, status = "revise", f"revise ({revision + 1}/{MAX_REVISIONS})"
    else:
        decision, status = "escalate", "max revisions reached, sent to human"

    ev = _event(
        "evaluator",
        status,
        f"score {evaluation.score}/100 · {evaluation.verdict}",
        started,
        rubric=checks,
    )
    rt.audit.append(
        state["run_id"],
        "evaluator",
        inputs={"rubric": checks, "revision": revision},
        outputs={**evaluation.model_dump(), "decision": decision},
        duration_ms=ev["duration_ms"],
    )
    out: dict[str, Any] = {
        "evaluation": {**evaluation.model_dump(), "rubric": checks, "decision": decision},
        "feedback": feedback,
        "timeline": [ev],
    }
    if decision == "revise":
        out["revision"] = revision + 1
    if decision != "revise":
        out["impact"] = business_impact(state)
        out["status"] = "awaiting_approval"
    return out


def business_impact(state: dict[str, Any]) -> dict[str, Any]:
    """Projected reach, accounts and cost from the synthetic history. Clearly labelled estimates."""
    brief = state["audience"]
    past = state["evidence"]["past"]
    by_channel = {r["channel"]: r for r in past["by_channel"]}
    primary = by_channel.get(brief["primary_channel"]) or next(iter(by_channel.values()), None)
    reach = brief["projected_reach"]
    if not primary:
        return {"reach": reach, "note": "no campaign history for this product"}
    responses = reach * primary["response_rate"]
    accounts = responses * primary["conversion_rate"]
    cost = reach * primary["cost_per_contact"]
    return {
        "reach": reach,
        "channel": primary["channel"],
        "expected_response_rate": primary["response_rate"],
        "expected_conversion_rate": primary["conversion_rate"],
        "projected_responses": round(responses),
        "projected_accounts": round(accounts),
        "estimated_cost_usd": round(cost, 2),
        "cost_per_acquired_account_usd": round(cost / accounts, 2) if accounts else None,
        "historical_cost_per_account_usd": primary["cost_per_account"],
        "compliance_issues_caught": state.get("issues_caught", 0),
        "revisions": state.get("revision", 0),
        "basis": (
            f"{primary['campaigns']} past {primary['channel'].replace('_', ' ')} campaigns in the "
            "synthetic Northwind dataset. Estimates only."
        ),
    }


# ---------------------------------------------------------------- publish


async def publish(state: dict[str, Any], rt: Runtime) -> dict[str, Any]:
    """Only reachable after a human approves (the graph interrupts before this node)."""
    started = time.perf_counter()
    decision = state.get("decision")
    if decision != "approve":
        ev = _event("publish", "rejected", "campaign rejected by reviewer", started)
        rt.audit.append(state["run_id"], "publish", outputs={"decision": decision or "none"})
        return {"status": "rejected", "timeline": [ev]}
    ev = _event("publish", "published", "campaign released to channels (simulated)", started)
    rt.audit.append(
        state["run_id"],
        "publish",
        outputs={"decision": "approve", "pieces": 4},
        duration_ms=ev["duration_ms"],
    )
    return {"status": "published", "timeline": [ev]}
