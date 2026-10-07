"""Build the synthetic Northwind Community Bank database.

Everything is generated from a fixed seed, so `make data` always produces the same file.
Only the Python standard library is used. Run:

    python -m campaign_copilot.data.generate            # writes data/northwind.db
    python -m campaign_copilot.data.generate --db x.db  # custom path
"""

from __future__ import annotations

import argparse
import random
import sqlite3
from pathlib import Path

SEED = 42
N_CUSTOMERS = 5000

# 12 branches. Eight are in the Dallas-Fort Worth metro, four elsewhere in North Texas.
BRANCHES = [
    (1, "Uptown", "Dallas", "Dallas-Fort Worth", 1998, 14),
    (2, "Oak Lawn", "Dallas", "Dallas-Fort Worth", 2004, 11),
    (3, "Lakewood", "Dallas", "Dallas-Fort Worth", 2009, 9),
    (4, "Preston Hollow", "Dallas", "Dallas-Fort Worth", 2012, 10),
    (5, "Plano Legacy", "Plano", "Dallas-Fort Worth", 2006, 12),
    (6, "Fort Worth Downtown", "Fort Worth", "Dallas-Fort Worth", 2001, 13),
    (7, "Arlington Center", "Arlington", "Dallas-Fort Worth", 2010, 8),
    (8, "Irving Las Colinas", "Irving", "Dallas-Fort Worth", 2015, 9),
    (9, "Frisco Main", "Frisco", "North Texas", 2017, 8),
    (10, "Denton Square", "Denton", "North Texas", 2008, 7),
    (11, "McKinney Historic", "McKinney", "North Texas", 2014, 7),
    (12, "Waco Riverfront", "Waco", "North Texas", 2003, 6),
]

SEGMENTS = ["young_professional", "family", "retiree", "small_business", "student"]
SEGMENT_WEIGHTS = [0.28, 0.30, 0.18, 0.12, 0.12]

PRODUCTS = ["checking", "savings", "credit_card", "mortgage", "auto_loan"]
CHANNELS = ["direct_mail", "email", "digital_ad"]

# Rough per-channel economics. Costs are per piece sent; response and conversion are base rates
# that get nudged by product and segment below. All of this is invented.
CHANNEL_ECON = {
    "direct_mail": {"cost": 0.82, "response": 0.031, "convert": 0.42},
    "email": {"cost": 0.04, "response": 0.018, "convert": 0.30},
    "digital_ad": {"cost": 0.19, "response": 0.012, "convert": 0.25},
}
PRODUCT_LIFT = {
    "checking": 1.15,
    "savings": 1.05,
    "credit_card": 0.85,
    "mortgage": 0.55,
    "auto_loan": 0.75,
}

OFFERS = {
    "checking": [
        ("$200 bonus for new checking with direct deposit", None),
        ("No-fee checking for 12 months", None),
    ],
    "savings": [("4.10% APY high-yield savings", 4.10), ("3.75% APY savings, no minimum", 3.75)],
    "credit_card": [("0% intro APR for 15 months", None), ("2% cash back on everything", None)],
    "mortgage": [
        ("Rate-lock refinance review", None),
        ("First-time buyer closing-cost credit", None),
    ],
    "auto_loan": [
        ("5.49% APR auto refinance", None),
        ("90 days no payment on new auto loans", None),
    ],
}


def _customer(rng: random.Random, cid: int) -> tuple:
    branch_id = rng.choices(range(1, 13), weights=[11, 9, 8, 8, 10, 10, 7, 7, 8, 6, 6, 5])[0]
    segment = rng.choices(SEGMENTS, weights=SEGMENT_WEIGHTS)[0]

    tenure = round(rng.lognormvariate(1.2, 0.8), 1)
    tenure = min(tenure, 38.0)

    # Product mix depends on the segment. Students rarely have mortgages;
    # retirees rarely need auto loans.
    p = {
        "young_professional": (0.78, 0.55, 0.50, 0.12, 0.30),
        "family": (0.85, 0.70, 0.55, 0.45, 0.40),
        "retiree": (0.80, 0.80, 0.35, 0.10, 0.08),
        "small_business": (0.90, 0.60, 0.65, 0.30, 0.25),
        "student": (0.60, 0.40, 0.20, 0.01, 0.10),
    }[segment]
    has = tuple(int(rng.random() < x) for x in p)

    base_chk = {
        "young_professional": 3200,
        "family": 5400,
        "retiree": 7800,
        "small_business": 14000,
        "student": 650,
    }
    base_sav = {
        "young_professional": 6500,
        "family": 11000,
        "retiree": 42000,
        "small_business": 21000,
        "student": 900,
    }
    chk = round(rng.lognormvariate(0, 0.9) * base_chk[segment], 2) if has[0] else 0.0
    sav = round(rng.lognormvariate(0, 1.0) * base_sav[segment], 2) if has[1] else 0.0

    engagement = {
        "young_professional": rng.betavariate(5, 2),
        "family": rng.betavariate(3, 3),
        "retiree": rng.betavariate(2, 5),
        "small_business": rng.betavariate(4, 3),
        "student": rng.betavariate(6, 2),
    }[segment]

    mail_opt = int(rng.random() < (0.55 if segment == "retiree" else 0.38))
    email_opt = int(rng.random() < (0.45 if segment == "retiree" else 0.72))
    last_contact = rng.randint(3, 240)

    return (
        cid,
        branch_id,
        segment,
        tenure,
        *has,
        chk,
        sav,
        round(engagement, 3),
        mail_opt,
        email_opt,
        last_contact,
    )


def _campaigns(rng: random.Random) -> list[tuple]:
    rows = []
    cid = 1
    quarters = [
        "2024-Q3",
        "2024-Q4",
        "2025-Q1",
        "2025-Q2",
        "2025-Q3",
        "2025-Q4",
        "2026-Q1",
        "2026-Q2",
    ]
    for q in quarters:
        for _ in range(6):
            product = rng.choices(PRODUCTS, weights=[0.35, 0.25, 0.18, 0.10, 0.12])[0]
            channel = rng.choice(CHANNELS)
            branch_id = rng.choice([None, None, rng.randint(1, 12)])
            segment = rng.choice([None, None, *SEGMENTS])
            offer, apy = rng.choice(OFFERS[product])
            econ = CHANNEL_ECON[channel]

            sent = rng.randint(400, 2200) if branch_id else rng.randint(3000, 9000)
            resp_rate = econ["response"] * PRODUCT_LIFT[product] * rng.uniform(0.7, 1.35)
            if segment == "retiree" and channel == "direct_mail":
                resp_rate *= 1.4
            if segment in ("student", "young_professional") and channel == "digital_ad":
                resp_rate *= 1.3
            responses = max(1, int(sent * resp_rate))
            opened = max(0, int(responses * econ["convert"] * rng.uniform(0.75, 1.2)))
            cost = round(sent * econ["cost"] + rng.uniform(150, 900), 2)  # plus creative/setup

            name = f"{q} {product.replace('_', ' ').title()} {channel.replace('_', ' ').title()}"
            if branch_id:
                name += f" (branch {branch_id})"
            rows.append(
                (
                    cid,
                    name,
                    q,
                    product,
                    channel,
                    branch_id,
                    segment,
                    offer,
                    apy,
                    sent,
                    responses,
                    opened,
                    cost,
                )
            )
            cid += 1
    return rows


def build(db_path: str | Path, seed: int = SEED, n_customers: int = N_CUSTOMERS) -> Path:
    """Create (or overwrite) the SQLite database and return its path."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    rng = random.Random(seed)
    schema = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")

    with sqlite3.connect(db_path) as con:
        con.executescript(schema)
        con.executemany("INSERT INTO branches VALUES (?,?,?,?,?,?)", BRANCHES)
        con.executemany(
            "INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (_customer(rng, i) for i in range(1, n_customers + 1)),
        )
        con.executemany("INSERT INTO campaigns VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", _campaigns(rng))
        con.commit()
    return db_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the synthetic Northwind database.")
    parser.add_argument("--db", default="data/northwind.db")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    path = build(args.db, args.seed)
    with sqlite3.connect(path) as con:
        n_c = con.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        n_b = con.execute("SELECT COUNT(*) FROM branches").fetchone()[0]
        n_k = con.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
    print(f"wrote {path}: {n_c} customers, {n_b} branches, {n_k} past campaigns (seed {args.seed})")


if __name__ == "__main__":
    main()
