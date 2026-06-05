import { StatusDot } from "./StatusDot";
import type { ReportSummary } from "@/lib/api";

const LABELS: Record<string, string> = {
  trajectory_determinism: "trajectory determinism",
  decision_determinism: "decision determinism",
  faithfulness: "faithfulness",
  consistency_under_repetition: "consistency-under-repetition",
};

function scoreStatus(value: number): "nominal" | "warning" | "failure" {
  if (value >= 0.9) return "nominal";
  if (value >= 0.6) return "warning";
  return "failure";
}

export function ReliabilityPanel({ report }: { report: ReportSummary | null }) {
  return (
    <section className="border border-border-1 bg-surface-1 p-8">
      <div className="flex items-baseline justify-between mb-6">
        <h2 className="text-sm font-mono uppercase tracking-widest text-text-lo">
          reliability surface
        </h2>
        {report ? (
          <StatusDot
            status={report.verdict === "ship" ? "nominal" : "failure"}
            label={`verdict: ${report.verdict.replace("_", " ")}`}
          />
        ) : (
          <StatusDot status="muted" label="awaiting first run" />
        )}
      </div>
      <ul className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(LABELS).map(([key, label]) => {
          const value = report?.aggregate?.[key];
          const status = value !== undefined ? scoreStatus(value) : "muted";
          return (
            <li
              key={key}
              className="flex items-baseline justify-between border-b border-border-1 pb-3"
            >
              <span className="text-text-lo text-sm">{label}</span>
              <span
                className={`font-mono text-2xl ${
                  status === "nominal"
                    ? "text-signal-nominal"
                    : status === "warning"
                    ? "text-signal-warning"
                    : status === "failure"
                    ? "text-signal-failure"
                    : "text-text-mute"
                }`}
              >
                {value !== undefined ? value.toFixed(3) : "—"}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
