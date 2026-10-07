import type { Impact, RunState } from "../types";

const usd = (n?: number | null) =>
  n === undefined || n === null ? "–" : n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const num = (n?: number) =>
  n === undefined ? "–" : n.toLocaleString("en-US", { maximumFractionDigits: n < 10 ? 1 : 0 });
const pct = (n?: number) => (n === undefined ? "–" : `${(n * 100).toFixed(1)}%`);

export function ImpactPanel({ impact, state }: { impact?: Impact; state?: RunState }) {
  if (!impact) {
    return (
      <aside className="impact muted">
        <h3>Business impact</h3>
        <p>Appears once the evaluator accepts a draft.</p>
      </aside>
    );
  }
  return (
    <aside className="impact">
      <h3>Business impact</h3>
      <p className="tiny">Projected from the synthetic Northwind dataset. Estimates only.</p>
      <dl>
        <div>
          <dt>Projected reach</dt>
          <dd>{num(impact.reach)}</dd>
        </div>
        <div>
          <dt>Primary channel</dt>
          <dd>{impact.channel?.replace("_", " ") ?? "–"}</dd>
        </div>
        <div>
          <dt>Expected response</dt>
          <dd>{pct(impact.expected_response_rate)}</dd>
        </div>
        <div>
          <dt>Projected new accounts</dt>
          <dd className="big">{num(impact.projected_accounts)}</dd>
        </div>
        <div>
          <dt>Estimated spend</dt>
          <dd>{usd(impact.estimated_cost_usd)}</dd>
        </div>
        <div>
          <dt>Cost per acquired account</dt>
          <dd className="big">{usd(impact.cost_per_acquired_account_usd)}</dd>
        </div>
        <div>
          <dt>Compliance issues caught</dt>
          <dd className="big">{impact.compliance_issues_caught}</dd>
        </div>
        <div>
          <dt>Revisions</dt>
          <dd>{impact.revisions}</dd>
        </div>
      </dl>
      {state?.evaluation && (
        <p className="tiny">
          Evaluator score {state.evaluation.score}/100 · {state.evaluation.verdict}
        </p>
      )}
      {impact.basis && <p className="tiny">{impact.basis}</p>}
    </aside>
  );
}
