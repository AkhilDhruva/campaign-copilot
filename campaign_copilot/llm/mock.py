"""Deterministic stand-ins for the model, one builder per agent.

Each builder receives the same `context` dict the real prompt is rendered from and returns a
validated schema object. There is no randomness anywhere in this file.

The copy builder deliberately writes a first draft with two classic compliance problems
("guaranteed" and "FREE" without terms) and fixes them on revision 1. That makes the
compliance -> evaluator -> copy loop visible in the demo and testable offline.
"""

from __future__ import annotations

import re
from typing import Any

from campaign_copilot.agents.schemas import (
    Ad,
    AudienceBrief,
    ComplianceFixes,
    CopyDraft,
    Evaluation,
    Fix,
    Plan,
    SegmentPick,
)

PRODUCT_WORDS = {
    "checking": ["checking", "deposit", "deposits", "dda"],
    "savings": ["savings", "high-yield", "high yield", "apy", "money market"],
    "credit_card": ["credit card", "card", "cards"],
    "mortgage": ["mortgage", "home loan", "refinance", "refi"],
    "auto_loan": ["auto", "car loan", "vehicle"],
}

PRODUCT_LABEL = {
    "checking": "checking account",
    "savings": "high-yield savings account",
    "credit_card": "credit card",
    "mortgage": "mortgage",
    "auto_loan": "auto loan",
}

PLACES = [
    "dallas-fort worth",
    "dfw",
    "dallas",
    "fort worth",
    "plano",
    "arlington",
    "irving",
    "frisco",
    "denton",
    "mckinney",
    "waco",
    "north texas",
]


def detect_product(goal: str) -> str:
    g = goal.lower()
    for product, words in PRODUCT_WORDS.items():
        if any(w in g for w in words):
            return product
    return "checking"


def detect_location(goal: str) -> str:
    g = goal.lower()
    for place in PLACES:
        if place in g:
            return place.title() if place != "dfw" else "DFW"
    return "all"


def detect_metric(goal: str, product: str) -> str:
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", goal)
    if m:
        return f"+{m.group(1)}% {product.replace('_', ' ')}"
    m = re.search(r"(\d[\d,]*)\s+(new\s+)?(accounts?|customers?|cards?|loans?)", goal, re.I)
    if m:
        return f"{m.group(1)} new {product.replace('_', ' ')} {m.group(3)}"
    return f"grow {product.replace('_', ' ')}"


def detect_timeframe(goal: str) -> str:
    g = goal.lower()
    for word in (
        "this quarter",
        "next quarter",
        "this month",
        "next month",
        "this year",
        "q1",
        "q2",
        "q3",
        "q4",
    ):
        if word in g:
            return word
    m = re.search(r"by (\w+ \d{4}|\w+)", g)
    return m.group(0) if m else "this quarter"


def build_plan(ctx: dict[str, Any]) -> Plan:
    goal = ctx["goal"]
    product = detect_product(goal)
    location = detect_location(goal)
    hints = {
        "checking": ["young_professional", "family"],
        "savings": ["retiree", "family"],
        "credit_card": ["young_professional", "small_business"],
        "mortgage": ["family", "young_professional"],
        "auto_loan": ["family", "young_professional"],
    }[product]
    return Plan(
        product=product,
        objective=f"{goal.strip().rstrip('.')}.",
        target_metric=detect_metric(goal, product),
        location=location,
        timeframe=detect_timeframe(goal),
        steps=[
            f"Resolve '{location}' to branch ids and pull branch performance",
            f"Find customers at those branches who do not yet hold a {PRODUCT_LABEL[product]}",
            "Compare past campaign economics by channel for this product",
            "Pick two or three segments and a primary/secondary channel",
            "Draft a letter, an email and two digital ads that cite the data",
            "Run the compliance rulebook and fix every flag",
            "Score the copy and loop back at most twice",
            "Hold for human approval before anything ships",
        ],
        segment_hints=hints,
    )


def build_audience(ctx: dict[str, Any]) -> AudienceBrief:
    plan: Plan = ctx["plan"]
    segments_data = ctx["segments"]  # query_segments result
    past = ctx["past"]  # past_campaign_results result
    branch_ids = ctx["branch_ids"]

    # Rank segments by how many reachable customers they contribute.
    ranked = sorted(segments_data["by_segment"], key=lambda r: r["customers"], reverse=True)
    preferred = [s for s in ranked if s["segment"] in plan.segment_hints] or ranked
    picks = []
    for row in (preferred + [r for r in ranked if r not in preferred])[:3]:
        picks.append(
            SegmentPick(
                segment=row["segment"],
                customers=row["customers"],
                reason=(
                    f"{row['customers']:,} customers without a {PRODUCT_LABEL[plan.product]}, "
                    f"avg engagement {row['avg_engagement']:.2f}, mail opt-in "
                    f"{row['direct_mail_opt_in_rate']:.0%}, "
                    f"email opt-in {row['email_opt_in_rate']:.0%}"
                ),
            )
        )

    by_channel = {r["channel"]: r for r in past["by_channel"]}
    ordered = sorted(by_channel.values(), key=lambda r: r["cost_per_account"])
    primary = ordered[0]["channel"] if ordered else "direct_mail"
    secondary = ordered[1]["channel"] if len(ordered) > 1 else "email"

    reach = sum(p.customers for p in picks)
    citations = [
        f"query_segments: {segments_data['customers']:,} customers at the chosen branches lack a "
        f"{PRODUCT_LABEL[plan.product]}",
    ]
    for row in ordered:
        citations.append(
            f"past_campaign_results: {row['channel'].replace('_', ' ')} averaged "
            f"{row['response_rate']:.1%} response and ${row['cost_per_account']:,.0f} per account "
            f"over {row['campaigns']} campaigns"
        )
    return AudienceBrief(
        branch_ids=branch_ids,
        segments=picks,
        primary_channel=primary,
        secondary_channel=secondary,
        projected_reach=reach,
        rationale=(
            f"Target the {len(picks)} largest segments without a {PRODUCT_LABEL[plan.product]} at "
            f"{len(branch_ids)} branches. Lead with {primary.replace('_', ' ')} because it has the "
            f"lowest historical cost per acquired account; "
            f"follow with {secondary.replace('_', ' ')}."
        ),
        data_citations=citations,
    )


def _offer(product: str) -> tuple[str, float | None, str]:
    return {
        "checking": (
            "Northwind Everyday Checking",
            None,
            "a $200 bonus when you set up direct deposit",
        ),
        "savings": ("Northwind High-Yield Savings", 4.10, "4.10% APY with no minimum balance"),
        "credit_card": ("Northwind Rewards Card", None, "2% cash back on every purchase"),
        "mortgage": ("Northwind Home Loans", None, "a free rate review with a local lender"),
        "auto_loan": ("Northwind Auto Refinance", None, "rates from 5.49% APR"),
    }[product]


def build_copy(ctx: dict[str, Any]) -> CopyDraft:
    plan: Plan = ctx["plan"]
    audience: AudienceBrief = ctx["audience"]
    revision: int = ctx.get("revision", 0)
    name, apy, hook = _offer(plan.product)
    label = PRODUCT_LABEL[plan.product]
    top = audience.segments[0]
    seg_word = top.segment.replace("_", " ")
    city = plan.location if plan.location != "all" else "North Texas"

    if revision == 0:
        # First draft: contains two things the rulebook will catch on purpose.
        promise = f"Guaranteed approval and FREE {label} for life"
        apy_line = f"Earn {apy}% APY" if apy else ""
    else:
        promise = f"A {label} built for {seg_word}s in {city}"
        apy_line = (
            f"Earn {apy:.2f}% Annual Percentage Yield (APY). APY is accurate as of the date "
            "of this "
            "offer and may change after the account is opened. Fees could reduce earnings."
            if apy
            else ""
        )

    letter = (
        f"Dear Neighbor,\n\n"
        f"{promise}. At Northwind Community Bank's {city} branches we are offering {hook}. "
        f"{apy_line}\n\n"
        f"Open your {name} online in minutes or visit any of our {len(audience.branch_ids)} nearby "
        f"branches. Offer available to new {label} customers through {plan.timeframe}.\n\n"
        f"Warm regards,\nThe Northwind {city} team\n\n"
        f"Member FDIC. Equal Housing Lender."
    )
    email_subject = f"{name}: {hook[:60]}"
    email_body = (
        f"Hi there,\n\n{promise}. {hook[0].upper() + hook[1:]} when you open a {name} "
        f"before the end of {plan.timeframe}. {apy_line}\n\n"
        f"Open online or stop by your {city} branch.\n\nNorthwind Community Bank · Member FDIC\n"
        "Unsubscribe | Northwind Community Bank, 100 Main Street, Dallas, TX 75201"
    )
    ads = [
        Ad(headline=f"{name}", body=f"{promise}. {hook[0].upper() + hook[1:]}. Member FDIC."),
        Ad(
            headline=f"{city} {label}s, done right",
            body=f"Join your neighbors at Northwind. {hook[0].upper() + hook[1:]}. Terms apply.",
        ),
    ]
    citations = [
        f"Lead segment is {seg_word} ({top.customers:,} reachable customers) from query_segments",
        f"Primary channel {audience.primary_channel.replace('_', ' ')} chosen for lowest "
        "cost per account "
        "from past_campaign_results",
        f"Letter emphasises branch proximity because {len(audience.branch_ids)} branches "
        "were resolved "
        "by resolve_branches",
    ]
    return CopyDraft(
        offer_name=name,
        offer_apy=apy,
        letter=letter,
        email_subject=email_subject,
        email_body=email_body,
        ads=ads,
        data_citations=citations,
    )


def build_fixes(ctx: dict[str, Any]) -> ComplianceFixes:
    issues = ctx["issues"]  # list of dicts from the rule checker
    fixes = []
    for issue in issues:
        rule = issue["rule"]
        if rule == "misleading_guarantee":
            s = "Remove 'guaranteed'. Approval depends on eligibility; say 'subject to approval'."
        elif rule == "free_without_terms":
            s = (
                "Either drop 'FREE' or state the conditions in the same sentence "
                "(e.g. 'no monthly fee with direct deposit')."
            )
        elif rule == "apy_without_disclosure":
            s = (
                "Add the APY disclosure: accuracy date, 'may change after opening', "
                "'fees could reduce earnings'."
            )
        elif rule == "protected_attribute":
            s = (
                "Remove the protected-class reference and target by product gap or "
                "engagement instead."
            )
        elif rule == "missing_fdic":
            s = "Add 'Member FDIC' to the piece."
        else:
            s = "Rewrite to follow the cited policy paragraph."
        fixes.append(Fix(issue_id=issue["id"], suggestion=s))
    return ComplianceFixes(fixes=fixes)


def build_evaluation(ctx: dict[str, Any]) -> Evaluation:
    rubric = ctx["rubric"]  # dict of check -> bool
    compliance_passed = ctx["compliance_passed"]
    passed = sum(1 for v in rubric.values() if v)
    score = round(100 * passed / max(len(rubric), 1))
    if not compliance_passed:
        score = min(score, 55)
    strengths = [k.replace("_", " ") for k, v in rubric.items() if v]
    weaknesses = [k.replace("_", " ") for k, v in rubric.items() if not v]
    if not compliance_passed:
        weaknesses.insert(0, "compliance issues outstanding")
    return Evaluation(
        score=score,
        strengths=strengths,
        weaknesses=weaknesses,
        verdict="accept" if compliance_passed and score >= 80 else "revise",
    )


BUILDERS = {
    "planner": build_plan,
    "audience": build_audience,
    "copy": build_copy,
    "compliance": build_fixes,
    "evaluator": build_evaluation,
}
