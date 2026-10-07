import { useEffect, useState } from "react";
import { api } from "../api";
import { replay } from "../replay";
import type { AuditRecord, VerifyResult } from "../types";

export function AuditView({ runId, demo }: { runId: string | null; demo: boolean }) {
  const [records, setRecords] = useState<AuditRecord[]>([]);
  const [verify, setVerify] = useState<VerifyResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    setError(null);
    try {
      if (demo) {
        const recs = await replay.audit();
        setRecords(recs);
        setVerify({
          ok: true,
          records: recs.length,
          first_bad_seq: null,
          reason: "recorded chain, verified when it was captured",
        });
        return;
      }
      setVerify(await api.verify());
      if (runId) setRecords(await api.audit(runId));
    } catch (e) {
      setError(String(e));
    }
  };

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId, demo]);

  return (
    <div className="audit">
      <div className="audit-head">
        <button onClick={refresh}>Verify chain</button>
        {verify && (
          <span className={`pill ${verify.ok ? "ok" : "bad"}`}>
            {verify.ok ? "intact" : `BROKEN at #${verify.first_bad_seq}`} · {verify.records}{" "}
            records · {verify.reason}
          </span>
        )}
        {error && <span className="pill bad">{error}</span>}
      </div>
      <p className="tiny">
        Each record's hash covers the previous hash plus its own content. Open{" "}
        <code>logs/audit.jsonl</code>, change any character, and press Verify: the chain breaks
        at that line.
      </p>
      {records.length > 0 ? (
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>step</th>
              <th>ms</th>
              <th>prev hash</th>
              <th>hash</th>
            </tr>
          </thead>
          <tbody>
            {records.map((r) => (
              <tr key={r.seq}>
                <td>{r.seq}</td>
                <td>{r.step}</td>
                <td>{r.duration_ms ?? ""}</td>
                <td className="hash">{r.prev_hash.slice(0, 12)}…</td>
                <td className="hash">{r.hash.slice(0, 12)}…</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="muted">Run a campaign first to see its audit trail.</p>
      )}
    </div>
  );
}
