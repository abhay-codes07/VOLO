// Pure parsing of a Volo Recording JSON into a trajectory view model.
// NB: this module must NOT import `vscode` — it is unit-tested in a plain Node/vitest environment.

export type StepStatus = "ok" | "warn";

export interface TrajectoryStep {
  index: number;
  kind: "model_call" | "tool_call" | "decision" | "unknown";
  title: string;
  detail: string;
  status: StepStatus;
}

export interface Trajectory {
  runId: string;
  framework: string;
  agent: string | null;
  steps: TrajectoryStep[];
  finalOutput: unknown;
}

interface RawPayload {
  type?: string;
  provider?: string;
  model?: string;
  tool?: string;
  label?: string;
  chosen?: string | null;
  request?: unknown;
  response?: unknown;
}

interface RawStep {
  payload?: RawPayload;
}

interface RawRecording {
  run_id?: string;
  agent_meta?: { framework?: string; agent_name?: string | null };
  steps?: RawStep[];
  final_output?: unknown;
}

function briefStep(index: number, payload: RawPayload): TrajectoryStep {
  const type = payload.type;
  if (type === "model_call") {
    return {
      index,
      kind: "model_call",
      title: `${payload.provider ?? "?"}/${payload.model ?? "?"}`,
      detail: "model call",
      // A model/tool call with no recorded response is unresolved — worth flagging.
      status: payload.response == null ? "warn" : "ok",
    };
  }
  if (type === "tool_call") {
    return {
      index,
      kind: "tool_call",
      title: String(payload.tool ?? "?"),
      detail: "tool call",
      status: payload.response == null ? "warn" : "ok",
    };
  }
  if (type === "decision") {
    const chosen = payload.chosen ? ` → ${payload.chosen}` : "";
    return {
      index,
      kind: "decision",
      title: `${payload.label ?? "decision"}${chosen}`,
      detail: "decision",
      status: "ok",
    };
  }
  return { index, kind: "unknown", title: String(type ?? "unknown"), detail: "", status: "ok" };
}

/** Parse a Recording (JSON string or already-parsed object) into a Trajectory view model. */
export function parseTrajectory(input: string | RawRecording): Trajectory {
  const raw: RawRecording = typeof input === "string" ? (JSON.parse(input) as RawRecording) : input;
  const steps = (raw.steps ?? []).map((s, i) => briefStep(i + 1, s.payload ?? {}));
  return {
    runId: raw.run_id ?? "(unknown)",
    framework: raw.agent_meta?.framework ?? "unknown",
    agent: raw.agent_meta?.agent_name ?? null,
    steps,
    finalOutput: raw.final_output ?? null,
  };
}

/** Summary counts by kind, for the header. */
export function stepCounts(t: Trajectory): Record<string, number> {
  const out: Record<string, number> = { model_call: 0, tool_call: 0, decision: 0, warn: 0 };
  for (const s of t.steps) {
    out[s.kind] = (out[s.kind] ?? 0) + 1;
    if (s.status === "warn") out.warn += 1;
  }
  return out;
}
