"""The compliance rule checker.

Each rule is a small deterministic test over one piece of copy. When a rule fires, the checker
runs a retrieval query against the policy index and attaches the best-matching policy
paragraph, so every flag says *which policy* and *what it says*. The model is only used
afterwards, to propose fixes; whether something is flagged never depends on a model.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from campaign_copilot.agents.schemas import CopyDraft
from campaign_copilot.compliance.retrieval import PolicyIndex

DEPOSIT_PRODUCTS = {"checking", "savings"}
CREDIT_PRODUCTS = {"credit_card", "mortgage", "auto_loan"}

PROTECTED_TERMS = [
    r"\bseniors?\b",
    r"\belderly\b",
    r"\bretirees?\b",
    r"\byoung families only\b",
    r"\b(for|designed for|perfect for|ideal for) (women|men|ladies|gentlemen)\b",
    r"\bimmigrants?\b",
    r"\bdisabled\b",
    r"\b(married|single) (people|customers|mothers|fathers)\b",
    r"\b(over|under) (50|55|60|65)\b",
    r"\b(christian|muslim|jewish|hindu)\b",
    r"\bpublic assistance\b",
    r"\bnational origin\b",
]


@dataclass
class Issue:
    id: str
    rule: str
    severity: str  # "block" or "warn"
    piece: str  # letter | email | ad_1 | ad_2
    snippet: str
    policy_id: str
    citation: str
    policy_text: str
    message: str
    fix: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ComplianceReport:
    passed: bool
    issues: list[Issue] = field(default_factory=list)
    checked_rules: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "issues": [i.to_dict() for i in self.issues],
            "checked_rules": self.checked_rules,
        }


# rule name -> (severity, retrieval query, human message)
RULES: dict[str, tuple[str, str, str]] = {
    "misleading_guarantee": (
        "block",
        "guaranteed approval pre-approved risk-free subject to approval",
        "Uses 'guaranteed' or similar. Approval depends on eligibility.",
    ),
    "free_without_terms": (
        "block",
        "word free only when no condition attached condition same sentence",
        "Says 'free' without stating the condition in the same sentence.",
    ),
    "unsubstantiated_superlative": (
        "warn",
        "superlatives best rate lowest fees require written substantiation",
        "Superlative claim needs written substantiation on file.",
    ),
    "apy_without_disclosure": (
        "block",
        "APY accurate as of date may change after opened fees could reduce earnings",
        "States a rate without the three required APY disclosures.",
    ),
    "apy_not_spelled_out": (
        "warn",
        "annual percentage yield APY written at least once",
        "APY must be spelled out as 'Annual Percentage Yield (APY)' at least once.",
    ),
    "protected_attribute": (
        "block",
        "protected characteristic age sex marital status national origin perfect for seniors",
        "Targets or references a protected class.",
    ),
    "missing_fdic": (
        "block",
        "deposit product must carry Member FDIC",
        "Deposit product piece lacks 'Member FDIC'.",
    ),
    "missing_equal_housing": (
        "block",
        "mortgage home-equity Equal Housing Lender statement",
        "Mortgage piece lacks 'Equal Housing Lender'.",
    ),
    "missing_bank_name": (
        "warn",
        "direct mail letters identify the bank full legal name",
        "Letter does not name Northwind Community Bank in full.",
    ),
    "ad_too_long": (
        "warn",
        "digital ads headline 90 characters body 300 characters",
        "Digital ad exceeds the length limit.",
    ),
    "missing_unsubscribe": (
        "block",
        "email unsubscribe link postal address CAN-SPAM",
        "Email lacks an unsubscribe link or postal address.",
    ),
    "jargon": (
        "warn",
        "eighth-grade reading level jargon DDA NOW account Reg DD",
        "Uses banking jargon customers do not understand.",
    ),
    "missing_end_date": (
        "warn",
        "offers that expire must state the end date or period limited time",
        "Says 'limited time' without an end date or period.",
    ),
}

_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")


def _pieces(copy: CopyDraft) -> dict[str, str]:
    return {
        "letter": copy.letter,
        "email": f"{copy.email_subject}\n{copy.email_body}",
        "ad_1": f"{copy.ads[0].headline}\n{copy.ads[0].body}",
        "ad_2": f"{copy.ads[1].headline}\n{copy.ads[1].body}",
    }


def _find(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, re.I)
    return text[max(0, m.start() - 30) : m.end() + 30].replace("\n", " ") if m else None


def _free_without_terms(text: str) -> str | None:
    for sentence in _SENTENCE.split(text):
        if re.search(r"\bfree\b", sentence, re.I):
            conditioned = re.search(
                r"\b(when|with|if|after|no monthly fee|no fee|at no cost with)\b", sentence, re.I
            )
            if not conditioned:
                return sentence.strip()[:120]
    return None


def check(copy: CopyDraft, product: str, index: PolicyIndex) -> ComplianceReport:
    issues: list[Issue] = []
    pieces = _pieces(copy)
    all_text = "\n".join(pieces.values())

    def flag(rule: str, piece: str, snippet: str) -> None:
        severity, query, message = RULES[rule]
        passage, _score = index.search(query, k=1)[0]
        issues.append(
            Issue(
                id=f"C{len(issues) + 1}",
                rule=rule,
                severity=severity,
                piece=piece,
                snippet=snippet,
                policy_id=passage.policy_id,
                citation=passage.citation,
                policy_text=passage.text,
                message=message,
            )
        )

    for piece, text in pieces.items():
        if snippet := _find(r"\b(guaranteed|pre-approved|risk-free)\b", text):
            flag("misleading_guarantee", piece, snippet)
        if snippet := _free_without_terms(text):
            flag("free_without_terms", piece, snippet)
        if snippet := _find(
            r"\b(best|lowest|#1|number one)\b[^.]{0,40}\b(rate|fee|fees|bank)\b", text
        ):
            flag("unsubstantiated_superlative", piece, snippet)
        for pattern in PROTECTED_TERMS:
            if snippet := _find(pattern, text):
                flag("protected_attribute", piece, snippet)
                break
        if snippet := _find(r"\b(DDA|NOW account|Reg DD)\b", text):
            flag("jargon", piece, snippet)
        if re.search(r"limited time", text, re.I) and not re.search(
            r"\b(through|until|ends?|by|before)\b", text, re.I
        ):
            flag("missing_end_date", piece, "limited time")

        mentions_rate = re.search(r"\bAPY\b|\d+(\.\d+)?\s?%\s?(APY|annual)", text, re.I)
        if mentions_rate:
            has_all = all(
                re.search(p, text, re.I)
                for p in (r"accurate as of", r"may change", r"fees (could|may) reduce")
            )
            if not has_all:
                flag(
                    "apy_without_disclosure",
                    piece,
                    _find(r"\bAPY\b|\d+(\.\d+)?\s?%", text) or "APY",
                )
            if not re.search(r"annual percentage yield", text, re.I):
                flag("apy_not_spelled_out", piece, "APY")

        if product in DEPOSIT_PRODUCTS and not re.search(r"member fdic", text, re.I):
            flag("missing_fdic", piece, text[:60])
        if product == "mortgage" and not re.search(r"equal housing lender", text, re.I):
            flag("missing_equal_housing", piece, text[:60])

    if not re.search(r"northwind community bank", copy.letter, re.I):
        flag("missing_bank_name", "letter", copy.letter[:60])
    if not re.search(r"unsubscribe", copy.email_body, re.I):
        flag("missing_unsubscribe", "email", copy.email_body[-80:])
    for n, ad in enumerate(copy.ads, start=1):
        if len(ad.headline) > 90 or len(ad.body) > 300:
            flag("ad_too_long", f"ad_{n}", ad.headline[:60])

    # Audience-level fair-lending check: segment names must not leak into copy as age words.
    if product in CREDIT_PRODUCTS and (snippet := _find(r"\bretiree|\bstudent", all_text)):
        flag("protected_attribute", "letter", snippet)

    blocking = [i for i in issues if i.severity == "block"]
    return ComplianceReport(passed=not blocking, issues=issues, checked_rules=list(RULES))
