from campaign_copilot.agents.schemas import Ad, CopyDraft
from campaign_copilot.compliance.retrieval import PolicyIndex, load_passages
from campaign_copilot.compliance.rules import check

POLICY_DIR = "policies"


def _draft(**overrides) -> CopyDraft:
    base = dict(
        offer_name="Northwind Everyday Checking",
        offer_apy=None,
        letter=(
            "Dear Neighbor,\nOpen a checking account with Northwind Community Bank and get a $200 "
            "bonus when you set up direct deposit. Offer ends December 31. Member FDIC."
        ),
        email_subject="A $200 welcome bonus",
        email_body="Open online today. Member FDIC. Unsubscribe | 100 Main St, Dallas TX",
        ads=[
            Ad(headline="Northwind Checking", body="$200 bonus with direct deposit. Member FDIC."),
            Ad(headline="Bank local", body="Open in minutes. Member FDIC. Terms apply."),
        ],
        data_citations=["x"],
    )
    base.update(overrides)
    return CopyDraft(**base)


def test_passages_load_with_ids():
    passages = load_passages(POLICY_DIR)
    ids = {p.policy_id for p in passages}
    assert {"1.1", "1.2", "2.2", "3.2", "4.1", "5.3"} <= ids
    assert all(p.text for p in passages)


def test_retrieval_finds_the_right_paragraph():
    index = PolicyIndex.from_dir(POLICY_DIR)
    top, _ = index.search("guaranteed approval pre-approved")[0]
    assert top.policy_id == "1.1"
    top, _ = index.search("APY accurate as of fees could reduce earnings")[0]
    assert top.policy_id == "2.2"
    top, _ = index.search("Member FDIC deposit product")[0]
    assert top.policy_id == "4.1"


def test_clean_copy_passes():
    index = PolicyIndex.from_dir(POLICY_DIR)
    report = check(_draft(), "checking", index)
    assert report.passed, [i.rule for i in report.issues]


def test_guarantee_and_free_are_blocked_with_citations():
    index = PolicyIndex.from_dir(POLICY_DIR)
    bad = _draft(
        letter="Guaranteed approval and FREE checking for life. Northwind Community Bank. Member FDIC."
    )
    report = check(bad, "checking", index)
    rules = {i.rule for i in report.issues}
    assert not report.passed
    assert {"misleading_guarantee", "free_without_terms"} <= rules
    guarantee = next(i for i in report.issues if i.rule == "misleading_guarantee")
    assert guarantee.policy_id == "1.1"
    assert "guaranteed" in guarantee.policy_text.lower()


def test_apy_needs_three_disclosures():
    index = PolicyIndex.from_dir(POLICY_DIR)
    bad = _draft(
        letter="Earn 4.10% APY on savings at Northwind Community Bank. Member FDIC.",
        offer_apy=4.1,
    )
    report = check(bad, "savings", index)
    assert "apy_without_disclosure" in {i.rule for i in report.issues}
    good = _draft(
        letter=(
            "Earn 4.10% Annual Percentage Yield (APY). APY is accurate as of today and may change "
            "after the account is opened. Fees could reduce earnings. Northwind Community Bank. "
            "Member FDIC."
        ),
        offer_apy=4.1,
    )
    assert check(good, "savings", index).passed


def test_protected_class_and_fdic_rules():
    index = PolicyIndex.from_dir(POLICY_DIR)
    bad = _draft(letter="Perfect for seniors. Northwind Community Bank.")
    rules = {i.rule for i in check(bad, "checking", index).issues}
    assert "protected_attribute" in rules
    assert "missing_fdic" in rules


def test_mortgage_needs_equal_housing():
    index = PolicyIndex.from_dir(POLICY_DIR)
    bad = _draft(letter="Refinance with Northwind Community Bank today, ends June 30.")
    assert "missing_equal_housing" in {i.rule for i in check(bad, "mortgage", index).issues}
