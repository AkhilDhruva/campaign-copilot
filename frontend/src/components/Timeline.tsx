import type { TimelineEvent } from "../types";

const LABELS: Record<string, string> = {
  start: "Goal received",
  planner: "Planner",
  audience: "Audience agent",
  copy: "Copy agent",
  compliance: "Compliance agent",
  evaluator: "Evaluator",
  approval: "Human approval",
  publish: "Publish",
  error: "Error",
};

function icon(status: string): string {
  if (status === "failed" || status === "error") return "✕";
  if (status === "waiting") return "⏸";
  if (status === "published") return "🚀";
  if (status === "rejected") return "⛔";
  if (status.startsWith("revise")) return "↻";
  return "✓";
}

function tone(status: string): string {
  if (status === "failed" || status === "error" || status === "rejected") return "bad";
  if (status === "waiting") return "wait";
  if (status.startsWith("revise")) return "warn";
  return "ok";
}

export function Timeline({ events, running }: { events: TimelineEvent[]; running: boolean }) {
  return (
    <ol className="timeline">
      {events.map((ev, i) => (
        <li key={i} className={`tl-item ${tone(ev.status)}`}>
          <span className="tl-icon">{icon(ev.status)}</span>
          <div className="tl-body">
            <div className="tl-head">
              <strong>{LABELS[ev.step] ?? ev.step}</strong>
              {ev.duration_ms !== undefined && <span className="tl-ms">{Math.round(ev.duration_ms)} ms</span>}
            </div>
            <div className="tl-summary">{ev.summary}</div>
            {ev.tool_calls && ev.tool_calls.length > 0 && (
              <ul className="tl-tools">
                {ev.tool_calls.map((c, j) => (
                  <li key={j} title={JSON.stringify(c.args)}>
                    <code>{c.tool}</code> → {c.error ? `error: ${c.error}` : c.summary}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </li>
      ))}
      {running && (
        <li className="tl-item live">
          <span className="tl-icon spinner" />
          <div className="tl-body">
            <div className="tl-summary">working…</div>
          </div>
        </li>
      )}
    </ol>
  );
}
