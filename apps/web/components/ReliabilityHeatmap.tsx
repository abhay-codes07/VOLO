import type { ReliabilityReport } from "@/lib/api";

const METRIC_KEYS = [
  "trajectory_determinism",
  "decision_determinism",
  "faithfulness",
  "consistency_under_repetition",
] as const;

const METRIC_LABEL: Record<(typeof METRIC_KEYS)[number], string> = {
  trajectory_determinism:        "trajectory",
  decision_determinism:          "decision",
  faithfulness:                  "faithful",
  consistency_under_repetition:  "consistency",
};

function cellColor(v: number): string {
  if (v >= 0.9) return "var(--signal-nominal)";
  if (v >= 0.6) return "var(--signal-warning)";
  return "var(--signal-failure)";
}

function cellBg(v: number): string {
  if (v >= 0.9) return "rgba(61, 224, 184, 0.16)";
  if (v >= 0.6) return "rgba(246, 183, 60, 0.20)";
  return "rgba(255, 92, 108, 0.22)";
}

export function ReliabilityHeatmap({ report }: { report: ReliabilityReport | null }) {
  if (!report || report.scenarios.length === 0) {
    return (
      <div className="hairline bg-surface-1 p-12 text-center font-mono text-sm text-text-mute">
        reliability surface — no report loaded
      </div>
    );
  }

  return (
    <div className="hairline bg-surface-1 shadow-elev-1 overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-border-1 bg-surface-2/40">
        <div className="font-mono text-[11px] uppercase tracking-widest text-text-mute">
          reliability surface · 7 scenarios × 4 metrics
        </div>
        <div className="chip">{report.verdict === "ship" ? "verdict ship" : "verdict no_ship"}</div>
      </div>

      <div className="overflow-x-auto p-5">
        <table className="w-full font-mono text-xs border-separate border-spacing-y-1">
          <thead>
            <tr>
              <th className="text-left text-text-mute uppercase tracking-widest pr-4 pb-3 font-normal">
                scenario
              </th>
              {METRIC_KEYS.map((m) => (
                <th
                  key={m}
                  className="text-text-mute uppercase tracking-widest px-3 pb-3 text-center font-normal"
                >
                  {METRIC_LABEL[m]}
                </th>
              ))}
              <th className="text-text-mute uppercase tracking-widest px-3 pb-3 text-center font-normal">
                runs
              </th>
            </tr>
          </thead>
          <tbody>
            {report.scenarios.map((sc) => (
              <tr key={`${sc.scenario_op}-${sc.seed}`}>
                <td className="py-2 pr-4">
                  <div className="text-text-hi text-sm">{sc.scenario_op}</div>
                  <div className="text-text-mute text-[10px] uppercase tracking-widest mt-0.5">
                    {sc.failure_class.replace(/_/g, " ")}
                  </div>
                </td>
                {METRIC_KEYS.map((m) => {
                  const v = sc.metrics[m] ?? 0;
                  return (
                    <td
                      key={m}
                      className="text-center align-middle hairline"
                      style={{ background: cellBg(v) }}
                    >
                      <span
                        className="font-display font-semibold tracking-tighter text-base tabular block py-2 px-3"
                        style={{ color: cellColor(v) }}
                      >
                        {v.toFixed(2)}
                      </span>
                    </td>
                  );
                })}
                <td className="text-center text-text-lo px-3">{sc.n_runs}</td>
              </tr>
            ))}
            <tr>
              <td className="pt-4 pr-4 text-text-mute uppercase tracking-widest text-[10px] font-mono">
                aggregate · p5
              </td>
              {METRIC_KEYS.map((m) => {
                const v = report.aggregate[m] ?? 0;
                return (
                  <td
                    key={m}
                    className="text-center align-middle border-t border-border-2 pt-4"
                  >
                    <span
                      className="font-display font-semibold text-xl tabular tracking-tighter"
                      style={{ color: cellColor(v) }}
                    >
                      {v.toFixed(3)}
                    </span>
                  </td>
                );
              })}
              <td className="text-center text-text-mute pt-4">
                {report.scenarios.reduce((s, x) => s + x.n_runs, 0)}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
