import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import { Architecture } from "./components/Architecture";
import { AuditView } from "./components/AuditView";
import { CopyView } from "./components/CopyView";
import { ImpactPanel } from "./components/ImpactPanel";
import { Timeline } from "./components/Timeline";
import { replay } from "./replay";
import type { Health, Issue, RunState, TimelineEvent } from "./types";

const EXAMPLES = [
  "Grow checking deposits 10% at our Dallas branches this quarter",
  "Open 300 new high-yield savings accounts in Plano this quarter",
  "Drive credit card sign-ups among small businesses in Fort Worth",
  "Win 50 mortgage refinances in Frisco by March",
];

const REPO_URL = "https://github.com/AkhilDhruva/campaign-copilot";

type Tab = "copilot" | "architecture" | "audit";

export default function App() {
  const [tab, setTab] = useState<Tab>("copilot");
  const [health, setHealth] = useState<Health | null>(null);
  const [demo, setDemo] = useState(false);
  const [goal, setGoal] = useState(EXAMPLES[0]);
  const [runId, setRunId] = useState<string | null>(null);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [state, setState] = useState<RunState | null>(null);
  const [running, setRunning] = useState(false);
  const [deciding, setDeciding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const closeRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    api
      .health()
      .then(setHealth)
      .catch(() => {
        // No backend: switch to replay of a recorded run.
        setDemo(true);
        setHealth({
          ok: true,
          version: "replay",
          mock_llm: true,
          llm_backend: "recorded run",
          mcp_transport: "recorded",
          bank: "Northwind Community Bank (fictional)",
        });
      });
    return () => closeRef.current?.();
  }, []);

  const refresh = useCallback(async (id: string) => {
    const s = await api.getRun(id);
    setState(s);
    return s;
  }, []);

  const start = async () => {
    setError(null);
    setEvents([]);
    setState(null);
    setRunning(true);
    closeRef.current?.();
    try {
      if (demo) {
        const paused = await replay.paused();
        setGoal(paused.goal);
        setRunId(paused.run_id);
        closeRef.current = replay.play(
          paused.events,
          (ev) => setEvents((prev) => [...prev, ev]),
          () => {
            setRunning(false);
            setState(paused);
          },
        );
        return;
      }
      const { run_id } = await api.startRun(goal);
      setRunId(run_id);
      closeRef.current = api.events(
        run_id,
        (ev) => setEvents((prev) => [...prev, ev]),
        () => {
          setRunning(false);
          void refresh(run_id);
        },
      );
    } catch (e) {
      setRunning(false);
      setError(String(e));
    }
  };

  const decide = async (decision: "approve" | "reject") => {
    if (!runId) return;
    setDeciding(true);
    try {
      if (demo) {
        if (decision === "approve") {
          const published = await replay.published();
          setEvents(published.events);
          setState(published);
        } else if (state) {
          const ev: TimelineEvent = {
            node: "publish",
            step: "publish",
            status: "rejected",
            summary: "campaign rejected by reviewer",
          };
          setEvents((prev) => [...prev, ev]);
          setState({ ...state, status: "rejected", next: [] });
        }
        return;
      }
      const res = await api.decide(runId, decision);
      setEvents(res.events);
      await refresh(runId);
    } catch (e) {
      setError(String(e));
    } finally {
      setDeciding(false);
    }
  };

  // The compliance node ran once per draft, in order, so reports line up with drafts.
  const issuesByDraft: Issue[][] = (state?.compliance_history ?? []).map((r) => r.issues);
  const awaiting = state?.status === "awaiting_approval";

  return (
    <div className="app">
      <header className="top">
        <div>
          <h1>Campaign Copilot</h1>
          <p className="tagline">
            Multi-agent campaign planning for Northwind Community Bank (fictional)
          </p>
        </div>
        <nav>
          {(["copilot", "architecture", "audit"] as Tab[]).map((t) => (
            <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
              {t[0].toUpperCase() + t.slice(1)}
            </button>
          ))}
        </nav>
        <div className="badges">
          {health && (
            <>
              <span className={`pill ${health.mock_llm ? "warn" : "ok"}`}>
                {demo
                  ? "Replay of a recorded run"
                  : health.mock_llm
                    ? "MOCK_LLM: deterministic, no API calls"
                    : `live model · ${health.llm_backend}`}
              </span>
              <span className="pill">MCP {health.mcp_transport}</span>
            </>
          )}
          <a className="pill" href={REPO_URL} target="_blank" rel="noreferrer">
            code
          </a>
        </div>
      </header>

      {demo && (
        <div className="notice">
          This is a static replay of one recorded run of the agents, so the goal is fixed. Clone
          the repo and run <code>python manage.py api</code> to try your own goals with the live
          workflow (no API key needed).
        </div>
      )}
      {error && <div className="error">{error}</div>}

      {tab === "architecture" && <Architecture />}
      {tab === "audit" && <AuditView runId={runId} demo={demo} />}

      {tab === "copilot" && (
        <main className="grid">
          <section className="col left">
            <label htmlFor="goal">Marketing goal</label>
            <textarea
              id="goal"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              rows={3}
              readOnly={demo}
            />
            <div className="examples">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex}
                  className="chip"
                  onClick={() => setGoal(ex)}
                  disabled={running || demo}
                >
                  {ex.split(" ").slice(0, 5).join(" ")}…
                </button>
              ))}
            </div>
            <button
              className="primary"
              onClick={start}
              disabled={running || goal.trim().length < 8}
            >
              {running ? "Running…" : demo ? "Play the recorded run" : "Run the copilot"}
            </button>

            <h3>Agent timeline</h3>
            <Timeline events={events} running={running} />

            {state?.plan && (
              <details className="plan">
                <summary>
                  Plan · {state.plan.target_metric} · {state.plan.location} ·{" "}
                  {state.plan.timeframe}
                </summary>
                <ol>
                  {state.plan.steps.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ol>
              </details>
            )}
            {state?.audience && (
              <details className="plan">
                <summary>
                  Audience · {state.audience.projected_reach.toLocaleString()} customers ·{" "}
                  {state.audience.segments.length} segments
                </summary>
                <p>{state.audience.rationale}</p>
                <ul>
                  {state.audience.segments.map((s) => (
                    <li key={s.segment}>
                      <strong>{s.segment.replace("_", " ")}</strong>: {s.reason}
                    </li>
                  ))}
                </ul>
                <ul className="cites">
                  {state.audience.data_citations.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </details>
            )}
          </section>

          <section className="col center">
            {state?.drafts && state.drafts.length > 0 ? (
              <>
                <div className="approve-bar">
                  {awaiting && (
                    <>
                      <span className="pill wait">Waiting for your decision</span>
                      <button
                        className="primary"
                        onClick={() => decide("approve")}
                        disabled={deciding}
                      >
                        Approve
                      </button>
                      <button
                        className="danger"
                        onClick={() => decide("reject")}
                        disabled={deciding}
                      >
                        Reject
                      </button>
                    </>
                  )}
                  {state.status === "published" && (
                    <span className="pill ok">Published (simulated)</span>
                  )}
                  {state.status === "rejected" && (
                    <span className="pill bad">Rejected. Nothing shipped.</span>
                  )}
                  {state.compliance && (
                    <span className={`pill ${state.compliance.passed ? "ok" : "bad"}`}>
                      compliance {state.compliance.passed ? "passed" : "failed"}
                    </span>
                  )}
                </div>
                <CopyView
                  drafts={state.drafts}
                  issuesByDraft={issuesByDraft}
                  citations={state.audience?.data_citations ?? []}
                />
              </>
            ) : (
              <div className="placeholder">
                <p>
                  Type a goal and press <strong>Run the copilot</strong>.
                </p>
                <p className="tiny">
                  The planner breaks it down, the audience agent queries the data through MCP, the
                  copy agent drafts four pieces, compliance checks them against the rulebook, the
                  evaluator scores them, and then it waits for you.
                </p>
              </div>
            )}
          </section>

          <ImpactPanel impact={state?.impact} state={state ?? undefined} />
        </main>
      )}

      <footer className="tiny">
        Independent portfolio project by Akhil Reddy Gaddam. Northwind Community Bank is
        fictional; all data is synthetic.
      </footer>
    </div>
  );
}
