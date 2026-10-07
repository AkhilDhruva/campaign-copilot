// Replay mode: when no backend answers /api/health, the UI plays back a recorded run from
// public/demo/*.json. This is what the static portfolio deployment uses. Every number shown is
// from a real run of the mock-mode workflow; nothing is invented in the browser.

import type { AuditRecord, RunState, TimelineEvent } from "./types";

const STEP_DELAY_MS = 650;

async function load<T>(name: string): Promise<T> {
  const res = await fetch(`/demo/${name}.json`);
  if (!res.ok) throw new Error(`replay fixture ${name} missing`);
  return res.json() as Promise<T>;
}

export const replay = {
  async paused(): Promise<RunState> {
    return load<RunState>("run-paused");
  },
  async published(): Promise<RunState> {
    return load<RunState>("run-published");
  },
  async audit(): Promise<AuditRecord[]> {
    return load<AuditRecord[]>("audit");
  },

  /** Emit the recorded events one by one, like the live SSE stream would. */
  play(events: TimelineEvent[], onEvent: (ev: TimelineEvent) => void, onDone: () => void) {
    let i = 0;
    let cancelled = false;
    const tick = () => {
      if (cancelled) return;
      if (i >= events.length) {
        onDone();
        return;
      }
      onEvent(events[i++]);
      setTimeout(tick, STEP_DELAY_MS);
    };
    setTimeout(tick, 200);
    return () => {
      cancelled = true;
    };
  },
};
