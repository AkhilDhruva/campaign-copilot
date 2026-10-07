"""Read-only queries over the Northwind database.

These are the functions the MCP server exposes as tools. They are plain Python so the
agents can also call them in-process during tests, and so every number the agents cite
can be traced to one SQL statement here.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

PRODUCT_COLUMNS = {
    "checking": "has_checking",
    "savings": "has_savings",
    "credit_card": "has_credit_card",
    "mortgage": "has_mortgage",
    "auto_loan": "has_auto_loan",
}


def default_db() -> Path:
    """Database path from the NORTHWIND_DB environment variable, read at call time."""
    return Path(os.environ.get("NORTHWIND_DB", "data/northwind.db"))


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else default_db()
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run `python manage.py data` first.")
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def resolve_branches(
    location: str | None = None, branch_ids: list[int] | None = None, db_path=None
) -> list[dict[str, Any]]:
    """Turn a place name ("Dallas", "DFW", "Frisco") or explicit ids into branch rows.

    With no arguments every branch is returned.
    """
    with _connect(db_path) as con:
        if branch_ids:
            marks = ",".join("?" * len(branch_ids))
            rows = con.execute(f"SELECT * FROM branches WHERE branch_id IN ({marks})", branch_ids)
        elif location:
            loc = location.strip().lower()
            if loc in ("dfw", "dallas-fort worth", "dallas fort worth", "metroplex"):
                rows = con.execute("SELECT * FROM branches WHERE metro = 'Dallas-Fort Worth'")
            else:
                rows = con.execute(
                    "SELECT * FROM branches WHERE lower(city) = ? "
                    "OR lower(name) LIKE ? OR lower(metro) = ?",
                    (loc, f"%{loc}%", loc),
                )
        else:
            rows = con.execute("SELECT * FROM branches")
        return [dict(r) for r in rows]


def _branch_filter(branch_ids: list[int] | None) -> tuple[str, list]:
    if not branch_ids:
        return "", []
    return f" AND branch_id IN ({','.join('?' * len(branch_ids))})", list(branch_ids)


def query_segments(
    branch_ids: list[int] | None = None,
    segment: str | None = None,
    product_gap: str | None = None,
    min_engagement: float | None = None,
    channel: str | None = None,
    db_path=None,
) -> dict[str, Any]:
    """Count and profile customers that match a set of filters.

    product_gap="checking" means customers who do NOT yet hold that product.
    channel="direct_mail" | "email" keeps only customers opted in to that channel.
    Returns totals plus a per-segment breakdown, so the copy agent can cite both.
    """
    where, params = "WHERE 1=1", []
    bf, bp = _branch_filter(branch_ids)
    where += bf
    params += bp
    if segment:
        where += " AND segment = ?"
        params.append(segment)
    if product_gap:
        col = PRODUCT_COLUMNS.get(product_gap)
        if not col:
            raise ValueError(
                f"unknown product {product_gap!r}; choose from {sorted(PRODUCT_COLUMNS)}"
            )
        where += f" AND {col} = 0"
    if min_engagement is not None:
        where += " AND digital_engagement >= ?"
        params.append(float(min_engagement))
    if channel == "direct_mail":
        where += " AND direct_mail_opt_in = 1"
    elif channel == "email":
        where += " AND email_opt_in = 1"
    elif channel not in (None, "", "digital_ad"):
        raise ValueError("channel must be direct_mail, email or digital_ad")

    agg = (
        "COUNT(*) AS customers, ROUND(AVG(checking_balance),2) AS avg_checking_balance, "
        "ROUND(AVG(savings_balance),2) AS avg_savings_balance, "
        "ROUND(AVG(digital_engagement),3) AS avg_engagement, "
        "ROUND(AVG(tenure_years),1) AS avg_tenure_years, "
        "ROUND(AVG(direct_mail_opt_in),3) AS direct_mail_opt_in_rate, "
        "ROUND(AVG(email_opt_in),3) AS email_opt_in_rate"
    )
    with _connect(db_path) as con:
        total = dict(con.execute(f"SELECT {agg} FROM customers {where}", params).fetchone())
        by_segment = [
            dict(r)
            for r in con.execute(
                f"SELECT segment, {agg} FROM customers {where} "
                "GROUP BY segment ORDER BY customers DESC",
                params,
            )
        ]
    return {
        "filters": {
            "branch_ids": branch_ids,
            "segment": segment,
            "product_gap": product_gap,
            "min_engagement": min_engagement,
            "channel": channel,
        },
        **total,
        "by_segment": by_segment,
    }


def branch_performance(branch_ids: list[int] | None = None, db_path=None) -> list[dict[str, Any]]:
    """Deposit footprint and campaign history per branch."""
    bf, bp = _branch_filter(branch_ids)
    sql = f"""
        SELECT b.branch_id, b.name, b.city, b.metro, b.opened_year, b.staff_count,
               COUNT(c.customer_id) AS customers,
               SUM(c.has_checking) AS checking_holders,
               ROUND(SUM(c.checking_balance), 2) AS checking_deposits,
               ROUND(SUM(c.savings_balance), 2) AS savings_deposits,
               ROUND(AVG(c.digital_engagement), 3) AS avg_engagement,
               (SELECT COUNT(*) FROM campaigns k WHERE k.branch_id = b.branch_id) AS past_campaigns,
               (SELECT COALESCE(SUM(accounts_opened),0) FROM campaigns k
                    WHERE k.branch_id = b.branch_id)
                   AS accounts_opened_from_branch_campaigns
        FROM branches b LEFT JOIN customers c ON c.branch_id = b.branch_id
        WHERE 1=1 {bf.replace("branch_id", "b.branch_id")}
        GROUP BY b.branch_id ORDER BY b.branch_id
    """
    with _connect(db_path) as con:
        rows = [dict(r) for r in con.execute(sql, bp)]
    for r in rows:
        r["checking_penetration"] = (
            round(r["checking_holders"] / r["customers"], 3) if r["customers"] else 0.0
        )
    return rows


def past_campaign_results(
    product: str | None = None,
    channel: str | None = None,
    branch_ids: list[int] | None = None,
    segment: str | None = None,
    db_path=None,
) -> dict[str, Any]:
    """Past campaigns matching the filters, plus rolled-up economics per channel."""
    where, params = "WHERE 1=1", []
    if product:
        where += " AND product = ?"
        params.append(product)
    if channel:
        where += " AND channel = ?"
        params.append(channel)
    if branch_ids:
        marks = ",".join("?" * len(branch_ids))
        where += f" AND (branch_id IS NULL OR branch_id IN ({marks}))"
        params += list(branch_ids)
    if segment:
        where += " AND (target_segment IS NULL OR target_segment = ?)"
        params.append(segment)

    with _connect(db_path) as con:
        campaigns = [
            dict(r)
            for r in con.execute(f"SELECT * FROM campaigns {where} ORDER BY quarter", params)
        ]
        rollup = [
            dict(r)
            for r in con.execute(
                f"""SELECT channel, COUNT(*) AS campaigns, SUM(sent_count) AS sent,
                           ROUND(1.0*SUM(response_count)/SUM(sent_count), 4) AS response_rate,
                           ROUND(1.0*SUM(accounts_opened)/MAX(SUM(response_count),1), 4)
                               AS conversion_rate,
                           SUM(accounts_opened) AS accounts_opened,
                           ROUND(SUM(cost_usd), 2) AS cost_usd,
                           ROUND(SUM(cost_usd)/MAX(SUM(sent_count),1), 4) AS cost_per_contact,
                           ROUND(SUM(cost_usd)/MAX(SUM(accounts_opened),1), 2) AS cost_per_account
                    FROM campaigns {where} GROUP BY channel ORDER BY cost_per_account""",
                params,
            )
        ]
    return {
        "filters": {
            "product": product,
            "channel": channel,
            "branch_ids": branch_ids,
            "segment": segment,
        },
        "campaign_count": len(campaigns),
        "by_channel": rollup,
        "campaigns": campaigns,
    }
