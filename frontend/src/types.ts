// Shapes returned by the FastAPI backend. Kept loose on purpose: the UI never writes these.

export interface TimelineEvent {
  node: string;
  step: string;
  status: string;
  summary: string;
  duration_ms?: number;
  ts?: number;
  tool_calls?: ToolCall[];
  rubric?: Record<string, boolean>;
}

export interface ToolCall {
  tool: string;
  args: Record<string, unknown>;
  summary?: string;
  error?: string;
  duration_ms: number;
}

export interface Ad {
  headline: string;
  body: string;
}

export interface CopyDraft {
  offer_name: string;
  offer_apy: number | null;
  letter: string;
  email_subject: string;
  email_body: string;
  ads: Ad[];
  data_citations: string[];
}

export interface Issue {
  id: string;
  rule: string;
  severity: "block" | "warn";
  piece: string;
  snippet: string;
  policy_id: string;
  citation: string;
  policy_text: string;
  message: string;
  fix?: string | null;
}

export interface Impact {
  reach: number;
  channel?: string;
  expected_response_rate?: number;
  expected_conversion_rate?: number;
  projected_responses?: number;
  projected_accounts?: number;
  estimated_cost_usd?: number;
  cost_per_acquired_account_usd?: number | null;
  historical_cost_per_account_usd?: number;
  compliance_issues_caught: number;
  revisions: number;
  basis?: string;
  note?: string;
}

export interface RunState {
  run_id: string;
  goal: string;
  error: string | null;
  events: TimelineEvent[];
  status?: string;
  next?: string[];
  plan?: {
    product: string;
    objective: string;
    target_metric: string;
    location: string;
    timeframe: string;
    steps: string[];
  };
  audience?: {
    branch_ids: number[];
    segments: { segment: string; customers: number; reason: string }[];
    primary_channel: string;
    secondary_channel: string;
    projected_reach: number;
    rationale: string;
    data_citations: string[];
  };
  copy?: CopyDraft;
  drafts?: CopyDraft[];
  compliance?: { passed: boolean; issues: Issue[]; checked_rules: string[] };
  compliance_history?: { passed: boolean; issues: Issue[]; checked_rules: string[] }[];
  evaluation?: {
    score: number;
    strengths: string[];
    weaknesses: string[];
    verdict: string;
    decision: string;
    rubric: Record<string, boolean>;
  };
  revision?: number;
  issues_caught?: number;
  impact?: Impact;
  tool_calls?: ToolCall[];
}

export interface AuditRecord {
  seq: number;
  ts: number;
  run_id: string;
  step: string;
  prev_hash: string;
  hash: string;
  duration_ms?: number;
  [key: string]: unknown;
}

export interface VerifyResult {
  ok: boolean;
  records: number;
  first_bad_seq: number | null;
  reason: string;
}

export interface Health {
  ok: boolean;
  version: string;
  mock_llm: boolean;
  llm_backend: string;
  mcp_transport: string;
  bank: string;
}
