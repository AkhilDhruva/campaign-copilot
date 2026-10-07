"""Structured outputs for every agent.

Each agent asks the model for exactly one of these shapes. With a real model the SDK's
structured-output mode guarantees the JSON validates; in mock mode the mock builds the same
objects directly. Either way the rest of the pipeline only ever sees validated pydantic models.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Product = Literal["checking", "savings", "credit_card", "mortgage", "auto_loan"]
Channel = Literal["direct_mail", "email", "digital_ad"]
Segment = Literal["young_professional", "family", "retiree", "small_business", "student"]


class Plan(BaseModel):
    """Planner output: the goal broken into concrete steps."""

    product: Product
    objective: str = Field(description="One sentence restating the measurable goal")
    target_metric: str = Field(description='e.g. "+10% checking deposits"')
    location: str = Field(description='Place name to resolve to branches, or "all"')
    timeframe: str
    steps: list[str] = Field(min_length=3, max_length=8)
    segment_hints: list[Segment] = Field(default_factory=list)


class SegmentPick(BaseModel):
    segment: Segment
    customers: int
    reason: str


class AudienceBrief(BaseModel):
    """Audience agent output: who to target, on which channels, and why (with numbers)."""

    branch_ids: list[int]
    segments: list[SegmentPick] = Field(min_length=1, max_length=3)
    primary_channel: Channel
    secondary_channel: Channel
    projected_reach: int
    rationale: str
    data_citations: list[str] = Field(
        description="Plain-English facts pulled from tool results, each naming the tool"
    )


class Ad(BaseModel):
    headline: str = Field(max_length=90)
    body: str = Field(max_length=300)


class CopyDraft(BaseModel):
    """Copy agent output: one letter, one email, two digital ads."""

    offer_name: str
    offer_apy: float | None = Field(default=None, description="APY if the offer quotes a rate")
    letter: str
    email_subject: str
    email_body: str
    ads: list[Ad] = Field(min_length=2, max_length=2)
    data_citations: list[str] = Field(
        description="Which data point drove each creative choice, "
        "e.g. 'Retirees prefer mail (55% opt-in)'"
    )


class Fix(BaseModel):
    issue_id: str
    suggestion: str = Field(description="How to rewrite the flagged text so it complies")


class ComplianceFixes(BaseModel):
    """Compliance agent output: a fix for every flagged issue."""

    fixes: list[Fix]


class Evaluation(BaseModel):
    """Evaluator output: a holistic score with reasons."""

    score: int = Field(ge=0, le=100)
    strengths: list[str]
    weaknesses: list[str]
    verdict: Literal["accept", "revise"]
