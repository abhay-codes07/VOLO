import type { ReportSummary } from "@/lib/api";

export function VerdictBanner({
  report,
  agentLabel,
}: {
  report: ReportSummary | null;
  agentLabel?: string;
}) {
  if (!report) {
    return (
      <div className="border border-border-1 bg-surface-1 px-6 py-5 flex items-center justify-between">
        <div className="font-mono text-xs uppercase tracking-widest text-text-mute">
          verdict — awaiting first run
        </div>
        <div className="text-text-mute font-mono">—</div>
      </div>
    );
  }
  const ship = report.verdict === "ship";
  return (
    <div
      className={`border ${
        ship ? "border-signal-nominal" : "border-signal-failure"
      } bg-surface-1 px-6 py-5 flex items-center justify-between`}
    >
      <div>
        <div className="font-mono text-xs uppercase tracking-widest text-text-mute mb-1">
          verdict {agentLabel ? `— ${agentLabel}` : ""}
        </div>
        <div
          className={`font-display text-2xl ${
            ship ? "text-signal-nominal" : "text-signal-failure"
          }`}
        >
          {ship ? "SHIP" : "NO SHIP — REGRESSION DETECTED"}
        </div>
      </div>
      <div className="text-right font-mono text-xs text-text-lo">
        {Object.entries(report.aggregate).map(([k, v]) => (
          <div key={k} className="flex justify-end gap-3">
            <span className="text-text-mute">{k.replace(/_/g, " ")}</span>
            <span
              className={
                v >= 0.9
                  ? "text-signal-nominal"
                  : v >= 0.6
                  ? "text-signal-warning"
                  : "text-signal-failure"
              }
            >
              {v.toFixed(3)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
