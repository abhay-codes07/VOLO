// Thin fetch wrappers around the volo-api FastAPI service.

const API_BASE =
  process.env.NEXT_PUBLIC_VOLO_API ?? "http://localhost:8080";

export type RecordingSummary = {
  run_id: string;
  stem: string;
  created_at: string;
  agent_name: string | null;
  framework: string;
  n_steps: number;
  redaction_applied: boolean;
  final_output: unknown;
};

export type ReportSummary = {
  baseline_run_id: string;
  stem: string;
  agent_name: string | null;
  verdict: "ship" | "no_ship";
  aggregate: Record<string, number>;
  n_scenarios: number;
};

export type ScenarioReport = {
  scenario_op: string;
  failure_class: string;
  seed: number;
  n_runs: number;
  metrics: Record<string, number>;
  histogram: Record<string, number>;
  applicable: boolean;
  notes: string | null;
};

export type ReliabilityReport = {
  baseline_run_id: string;
  agent_name: string | null;
  fail_under: number;
  aggregate: Record<string, number>;
  verdict: "ship" | "no_ship";
  scenarios: ScenarioReport[];
};

export type ScenarioOperator = {
  name: string;
  failure_class: string;
  description: string;
};

export type StepPayload =
  | { type: "model_call"; provider: string; model: string; request: Record<string, unknown>; response: Record<string, unknown> | null }
  | { type: "tool_call"; tool: string; request: Record<string, unknown>; response: Record<string, unknown> | null }
  | { type: "decision"; label: string; chosen: string | null; rationale: string | null; options: string[] };

export type Step = {
  step_id: string;
  parent_id: string | null;
  started_at: string;
  latency_ms: number | null;
  tokens: number | null;
  cost_usd: number | null;
  payload: StepPayload;
};

export type Recording = {
  recording_schema_version: string;
  run_id: string;
  created_at: string;
  agent_meta: { framework: string; agent_name: string | null };
  steps: Step[];
  final_output: unknown;
};

export type StepDiff = {
  kind: "same" | "added" | "removed" | "changed";
  a_index: number | null;
  b_index: number | null;
  a: Record<string, unknown> | null;
  b: Record<string, unknown> | null;
  changed_keys: string[];
};

export type Diff = {
  baseline_run_id: string;
  candidate_run_id: string;
  first_diverging_step: number | null;
  aligned_steps: StepDiff[];
  summary: string;
};

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return (await res.json()) as T;
}

async function post<T, B>(path: string, body: B): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return (await res.json()) as T;
}

export const listRecordings   = () => get<RecordingSummary[]>("/recordings");
export const getRecording     = (id: string) => get<Recording>(`/recordings/${encodeURIComponent(id)}`);
export const listReports      = () => get<ReportSummary[]>("/reports");
export const getReport        = (id: string) => get<ReliabilityReport>(`/reports/${encodeURIComponent(id)}`);
export const listScenarios    = () => get<ScenarioOperator[]>("/scenarios");
export const getNamedDiff     = (stem: string) => get<Diff>(`/diffs/${encodeURIComponent(stem)}`);
export const computeDiff      = (baseline_id: string, candidate_id: string) =>
  post<Diff, { baseline_id: string; candidate_id: string }>("/diff", { baseline_id, candidate_id });

export async function safe<T>(p: Promise<T>): Promise<T | null> {
  try { return await p; } catch { return null; }
}
