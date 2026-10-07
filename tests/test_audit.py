import json

from campaign_copilot.audit import AuditLog, verify


def test_chain_links_and_verifies(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl")
    a = log.append("run1", "planner", inputs={"goal": "x"}, outputs={"steps": 3})
    b = log.append("run1", "audience", outputs={"reach": 10})
    assert a["seq"] == 1 and b["seq"] == 2
    assert b["prev_hash"] == a["hash"]
    result = verify(log.path)
    assert result["ok"] and result["records"] == 2


def test_resumes_chain_after_reopen(tmp_path):
    path = tmp_path / "audit.jsonl"
    AuditLog(path).append("r", "one")
    AuditLog(path).append("r", "two")
    recs = AuditLog(path).records()
    assert [r["seq"] for r in recs] == [1, 2]
    assert recs[1]["prev_hash"] == recs[0]["hash"]
    assert verify(path)["ok"]


def test_tampering_is_detected(tmp_path):
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    for i in range(4):
        log.append("r", f"step{i}", value=i)
    lines = path.read_text(encoding="utf-8").splitlines()

    # Edit a value in record 2 without touching its hash.
    rec = json.loads(lines[1])
    rec["value"] = 999
    lines[1] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = verify(path)
    assert not result["ok"] and result["first_bad_seq"] == 2

    # Deleting a line breaks the sequence.
    path.write_text("\n".join(l for i, l in enumerate(lines) if i != 1) + "\n", encoding="utf-8")
    assert verify(path)["first_bad_seq"] == 2


def test_records_filter_by_run(tmp_path):
    log = AuditLog(tmp_path / "a.jsonl")
    log.append("run-a", "x")
    log.append("run-b", "y")
    log.append("run-a", "z")
    assert [r["step"] for r in log.records("run-a")] == ["x", "z"]
