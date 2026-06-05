import type { Step } from "@/lib/api";

const TYPE_COLOR: Record<Step["payload"]["type"], string> = {
  model_call: "text-signal-info",
  tool_call: "text-signal-nominal",
  decision: "text-signal-warning",
};

function brief(payload: Step["payload"]): string {
  if (payload.type === "model_call") return `${payload.provider}/${payload.model}`;
  if (payload.type === "tool_call") return payload.tool;
  return payload.label;
}

export function TrajectoryList({ steps }: { steps: Step[] }) {
  if (steps.length === 0) {
    return (
      <p className="text-text-mute text-sm font-mono">trajectory is empty.</p>
    );
  }
  return (
    <ol className="font-mono text-sm divide-y divide-border-1">
      {steps.map((step, i) => (
        <li
          key={step.step_id}
          className="grid grid-cols-[3rem_8rem_1fr_6rem] items-baseline gap-4 py-3"
        >
          <span className="text-text-mute">{String(i + 1).padStart(3, "0")}</span>
          <span className={`${TYPE_COLOR[step.payload.type]}`}>{step.payload.type}</span>
          <span className="text-text-hi truncate">{brief(step.payload)}</span>
          <span className="text-text-mute text-right">
            {step.latency_ms !== null ? `${step.latency_ms.toFixed(1)} ms` : "—"}
          </span>
        </li>
      ))}
    </ol>
  );
}
