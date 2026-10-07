import type { AuditRecord, Health, RunState, TimelineEvent, VerifyResult } from "./types";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* keep statusText */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => fetch("/api/health").then(json<Health>),

  startRun: (goal: string) =>
    fetch("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal }),
    }).then(json<{ run_id: string }>),

  getRun: (runId: string) => fetch(`/api/runs/${runId}`).then(json<RunState>),

  decide: (runId: string, decision: "approve" | "reject") =>
    fetch(`/api/runs/${runId}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision }),
    }).then(json<{ status: string; events: TimelineEvent[] }>),

  audit: (runId: string) => fetch(`/api/audit/${runId}`).then(json<AuditRecord[]>),
  verify: () => fetch("/api/audit/verify").then(json<VerifyResult>),

  /** Subscribe to the live timeline. Returns a function that closes the stream. */
  events: (runId: string, onEvent: (ev: TimelineEvent) => void, onDone: () => void) => {
    const source = new EventSource(`/api/runs/${runId}/events`);
    source.onmessage = (msg) => {
      const ev = JSON.parse(msg.data) as TimelineEvent;
      onEvent(ev);
      if (["waiting", "published", "rejected", "error"].includes(ev.status)) {
        source.close();
        onDone();
      }
    };
    source.onerror = () => {
      source.close();
      onDone();
    };
    return () => source.close();
  },
};
