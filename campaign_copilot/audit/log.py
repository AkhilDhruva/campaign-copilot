"""Tamper-evident audit log.

One JSON object per line. Every record carries the SHA-256 of the previous record, and its own
hash covers (previous hash + its canonical JSON). Change, delete or reorder any line and every
later hash stops matching, so `verify()` can prove the log is intact or point at the first bad
line. This is the same idea as a blockchain's block hashing, without the consensus part.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any

GENESIS = "0" * 64


def canonical(obj: Any) -> str:
    """Stable JSON: sorted keys, no whitespace, unicode preserved."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def record_hash(prev_hash: str, record_without_hash: dict[str, Any]) -> str:
    return hashlib.sha256(
        (prev_hash + "\n" + canonical(record_without_hash)).encode("utf-8")
    ).hexdigest()


def default_path() -> Path:
    return Path(os.environ.get("AUDIT_LOG", "logs/audit.jsonl"))


class AuditLog:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else default_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._seq, self._last_hash = self._tail()

    def _tail(self) -> tuple[int, str]:
        """Resume the chain from the last line on disk."""
        if not self.path.exists() or self.path.stat().st_size == 0:
            return 0, GENESIS
        last = None
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    last = json.loads(line)
        if last is None:
            return 0, GENESIS
        return int(last["seq"]), str(last["hash"])

    def append(self, run_id: str, step: str, **fields: Any) -> dict[str, Any]:
        """Write one record and return it (including its hash)."""
        with self._lock:
            record = {
                "seq": self._seq + 1,
                "ts": time.time(),
                "run_id": run_id,
                "step": step,
                **fields,
                "prev_hash": self._last_hash,
            }
            record["hash"] = record_hash(self._last_hash, record)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(canonical(record) + "\n")
            self._seq = record["seq"]
            self._last_hash = record["hash"]
            return record

    def records(self, run_id: str | None = None) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out = []
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rec = json.loads(line)
                    if run_id is None or rec.get("run_id") == run_id:
                        out.append(rec)
        return out


def verify(path: str | Path | None = None) -> dict[str, Any]:
    """Walk the chain. Returns {"ok": bool, "records": n, "first_bad_seq": int|None, "reason": str}."""
    p = Path(path) if path else default_path()
    if not p.exists():
        return {"ok": True, "records": 0, "first_bad_seq": None, "reason": "empty"}
    prev = GENESIS
    n = 0
    with p.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                return {
                    "ok": False,
                    "records": n,
                    "first_bad_seq": lineno,
                    "reason": "unparseable line",
                }
            n += 1
            if rec.get("seq") != n:
                return {"ok": False, "records": n, "first_bad_seq": n, "reason": "sequence gap"}
            if rec.get("prev_hash") != prev:
                return {
                    "ok": False,
                    "records": n,
                    "first_bad_seq": n,
                    "reason": "previous hash mismatch",
                }
            claimed = rec.get("hash")
            body = {k: v for k, v in rec.items() if k != "hash"}
            if record_hash(prev, body) != claimed:
                return {
                    "ok": False,
                    "records": n,
                    "first_bad_seq": n,
                    "reason": "record hash mismatch",
                }
            prev = claimed
    return {"ok": True, "records": n, "first_bad_seq": None, "reason": "chain intact"}
