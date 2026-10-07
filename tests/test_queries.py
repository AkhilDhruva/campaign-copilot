import pytest

from campaign_copilot.data import queries as q


def test_resolve_branches_by_city(db_path):
    dallas = q.resolve_branches("Dallas", db_path=db_path)
    assert [b["branch_id"] for b in dallas] == [1, 2, 3, 4]
    assert len(q.resolve_branches("DFW", db_path=db_path)) == 8
    assert len(q.resolve_branches(db_path=db_path)) == 12
    assert q.resolve_branches("Nowhere", db_path=db_path) == []


def test_query_segments_product_gap(db_path):
    everyone = q.query_segments(db_path=db_path)
    no_checking = q.query_segments(product_gap="checking", db_path=db_path)
    assert everyone["customers"] == 5000
    assert 0 < no_checking["customers"] < everyone["customers"]
    # Customers without checking have zero checking balance by construction.
    assert no_checking["avg_checking_balance"] == 0
    assert {r["segment"] for r in no_checking["by_segment"]} <= {
        "young_professional",
        "family",
        "retiree",
        "small_business",
        "student",
    }


def test_query_segments_filters_compose(db_path):
    r = q.query_segments(
        branch_ids=[1, 2, 3, 4], product_gap="checking", channel="direct_mail", db_path=db_path
    )
    assert r["customers"] > 0
    assert r["direct_mail_opt_in_rate"] == 1.0
    assert r["filters"]["branch_ids"] == [1, 2, 3, 4]


def test_query_segments_rejects_bad_product(db_path):
    with pytest.raises(ValueError):
        q.query_segments(product_gap="crypto", db_path=db_path)


def test_branch_performance(db_path):
    rows = q.branch_performance(branch_ids=[1, 5], db_path=db_path)
    assert [r["branch_id"] for r in rows] == [1, 5]
    assert sum(r["customers"] for r in q.branch_performance(db_path=db_path)) == 5000
    assert all(0 <= r["checking_penetration"] <= 1 for r in rows)


def test_past_campaign_results(db_path):
    r = q.past_campaign_results(product="checking", db_path=db_path)
    assert r["campaign_count"] > 0
    assert all(c["product"] == "checking" for c in r["campaigns"])
    channels = {row["channel"] for row in r["by_channel"]}
    assert channels <= {"direct_mail", "email", "digital_ad"}
    assert all(row["cost_per_account"] > 0 for row in r["by_channel"])
    # Branch filter keeps bank-wide campaigns (branch_id NULL) plus the chosen branches.
    r2 = q.past_campaign_results(branch_ids=[1], db_path=db_path)
    assert all(c["branch_id"] in (None, 1) for c in r2["campaigns"])
