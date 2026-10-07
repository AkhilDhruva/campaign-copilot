"""Run every golden goal through the workflow and score the results.

Each goal carries expected properties (product, number of branches, required disclosures).
On top of those, every run must: pause for approval, pass compliance, be accepted by the
evaluator within the revision cap, cite data, and produce a business-impact estimate.

    python -m evals.run            # prints a table, writes evals/last_run.json
    python -m evals.run --json     # machine-readable only

Exit code is 1 when the overall score is below evals/baseline.json -> min_score.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

from campaign_copilot.audit import AuditLog, verify
from campaign_copilot.runner import CampaignRunner

HERE = Path(__file__).parent


def checks_for(expected: dict, state: dict) -> dict[str, bool]:
    copy = state.get("copy") or {}
    all_text = " ".join(
        [copy.get("letter", ""), copy.get("email_body", "")]
        + [a.get("body", "") for a in copy.get("ads", [])]
    )
    out = {
        "paused_for_approval": state.get("status") == "awaiting_approval"
        and state.get("next") == ["publish"],
        "product_detected": (state.get("plan") or {}).get("product") == expected["product"],
        "branch_count": len((state.get("audience") or {}).get("branch_ids", []))
        == expected["branches"],
        "compliance_passed": bool((state.get("compliance") or {}).get("passed")),
        "evaluator_accepted": (state.get("evaluation") or {}).get("decision") == "accept",
        "within_revision_cap": (state.get("revision") or 0) <= 2,
        "caught_first_draft_issues": (state.get("issues_caught") or 0) >= 1,
        "cites_data": len(copy.get("data_citations", [])) >= 2,
        "reach_positive": ((state.get("audience") or {}).get("projected_reach") or 0) > 0,
        "impact_present": (state.get("impact") or {}).get("projected_accounts") is not None
        and ((state.get("impact") or {}).get("estimated_cost_usd") or 0) > 0,
        "used_all_four_tools": {c["tool"] for c in state.get("tool_calls", [])}
        >= {"resolve_branches", "branch_performance", "query_segments", "past_campaign_results"},
        "no_protected_terms": not re.search(
            r"\b(seniors?|elderly|retirees?|immigrants?)\b", all_text, re.I
        ),
    }
    if expected.get("primary_channel_in"):
        out["primary_channel_expected"] = (state.get("audience") or {}).get(
            "primary_channel"
        ) in expected["primary_channel_in"]
    if expected.get("apy_disclosed"):
        out["apy_disclosed"] = bool(
            re.search(r"annual percentage yield", all_text, re.I)
            and re.search(r"fees could reduce", all_text, re.I)
        )
    if expected.get("equal_housing"):
        out["equal_housing_lender"] = "equal housing lender" in all_text.lower()
    return out


async def run_all(goals: list[dict], audit_path: Path) -> list[dict]:
    results = []
    async with CampaignRunner(audit=AuditLog(audit_path)) as runner:
        for g in goals:
            started = time.perf_counter()
            run_id = f"eval-{g['id']}"
            try:
                state = await runner.start(run_id, g["goal"])
                checks = checks_for(g, state)
                error = None
            except Exception as exc:  # a crash counts as every check failed
                checks = {"ran_without_error": False}
                error = f"{type(exc).__name__}: {exc}"
            results.append(
                {
                    "id": g["id"],
                    "goal": g["goal"],
                    "checks": checks,
                    "passed": sum(checks.values()),
                    "total": len(checks),
                    "error": error,
                    "seconds": round(time.perf_counter() - started, 2),
                }
            )
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="print JSON only")
    args = parser.parse_args()

    if os.environ.get("MOCK_LLM", "1") in ("0", "false"):
        print(
            "warning: MOCK_LLM=0, this eval will call the real model and cost money",
            file=sys.stderr,
        )

    golden = json.loads((HERE / "golden.json").read_text(encoding="utf-8"))
    baseline = json.loads((HERE / "baseline.json").read_text(encoding="utf-8"))
    audit_path = Path("logs") / "eval_audit.jsonl"
    if audit_path.exists():
        audit_path.unlink()

    results = asyncio.run(run_all(golden["goals"], audit_path))
    passed = sum(r["passed"] for r in results)
    total = sum(r["total"] for r in results)
    score = passed / total if total else 0.0
    chain = verify(audit_path)
    summary = {
        "score": round(score, 4),
        "passed_checks": passed,
        "total_checks": total,
        "goals": len(results),
        "goals_fully_passing": sum(r["passed"] == r["total"] for r in results),
        "min_score": baseline["min_score"],
        "audit_chain_ok": chain["ok"],
        "results": results,
    }
    (HERE / "last_run.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"\n{'id':5} {'pass':>5} {'sec':>5}  goal")
        print("-" * 78)
        for r in results:
            flag = (
                ""
                if r["passed"] == r["total"]
                else "  <- " + ", ".join(k for k, v in r["checks"].items() if not v)
            )
            print(
                f"{r['id']:5} {r['passed']:>2}/{r['total']:<2} {r['seconds']:>5}  "
                f"{r['goal'][:48]}{flag}"
            )
            if r["error"]:
                print(f"      error: {r['error']}")
        print("-" * 78)
        print(
            f"score {score:.1%} ({passed}/{total} checks) · "
            f"{summary['goals_fully_passing']}/{len(results)} goals fully passing · "
            f"audit chain {'intact' if chain['ok'] else 'BROKEN'} · "
            f"threshold {baseline['min_score']:.0%}"
        )
    ok = score >= baseline["min_score"] and chain["ok"]
    print("EVAL PASS" if ok else "EVAL FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
