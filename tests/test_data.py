"""The synthetic dataset must be the right shape and fully deterministic."""

import hashlib
import sqlite3

from campaign_copilot.data.generate import N_CUSTOMERS, build


def _sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_build_shape(tmp_path):
    db = build(tmp_path / "nw.db")
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == N_CUSTOMERS
        assert con.execute("SELECT COUNT(*) FROM branches").fetchone()[0] == 12
        assert con.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0] == 48
        # Every customer belongs to a real branch.
        orphans = con.execute(
            "SELECT COUNT(*) FROM customers WHERE branch_id NOT IN (SELECT branch_id FROM branches)"
        ).fetchone()[0]
        assert orphans == 0
        # Balances are only non-zero when the product is held.
        bad = con.execute(
            "SELECT COUNT(*) FROM customers WHERE (has_checking=0 AND checking_balance>0) "
            "OR (has_savings=0 AND savings_balance>0)"
        ).fetchone()[0]
        assert bad == 0


def test_build_is_deterministic(tmp_path):
    a = build(tmp_path / "a.db")
    b = build(tmp_path / "b.db")
    assert _sha(a) == _sha(b)


def test_seed_changes_output(tmp_path):
    a = build(tmp_path / "a.db", seed=1)
    b = build(tmp_path / "b.db", seed=2)
    assert _sha(a) != _sha(b)
