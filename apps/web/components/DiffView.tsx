import type { Diff, StepDiff } from "@/lib/api";

const KIND_COLOR: Record<StepDiff["kind"], string> = {
  same:    "var(--text-mute)",
  added:   "var(--signal-nominal)",
  removed: "var(--signal-failure)",
  changed: "var(--signal-warning)",
};

const KIND_MARKER: Record<StepDiff["kind"], string> = {
  same:    "=",
  added:   "+",
  removed: "−",
  changed: "~",
};

function payloadBrief(payload: Record<string, unknown> | null): string {
  if (!payload) return "—";
  const t = payload["type"] as string | undefined;
  if (t === "model_call") return `${payload["provider"]}/${payload["model"]}`;
  if (t === "tool_call")  return String(payload["tool"]);
  if (t === "decision")   return String(payload["label"]);
  return JSON.stringify(payload).slice(0, 80);
}

function responseSummary(payload: Record<string, unknown> | null): string {
  if (!payload) return "";
  const r = payload["response"];
  if (r === undefined || r === null) return "";
  return JSON.stringify(r);
}

export function DiffView({ diff }: { diff: Diff }) {
  return (
    <div className="hairline bg-surface-1 shadow-elev-1 overflow-hidden">
      <div className="border-b border-border-1 px-5 py-3 flex items-baseline justify-between bg-surface-2/40">
        <div className="font-mono text-[11px] uppercase tracking-widest text-text-mute">
          {diff.first_diverging_step === null
            ? "no divergence detected"
            : `first divergence at aligned step #${diff.first_diverging_step}`}
        </div>
        <div className="font-mono text-[11px] text-text-mute">{diff.summary}</div>
      </div>
      <table className="w-full font-mono text-xs">
        <thead>
          <tr className="text-text-mute uppercase tracking-widest">
            <th className="text-left px-4 py-3 w-12 font-normal">#</th>
            <th className="text-left px-4 py-3 w-6 font-normal"></th>
            <th className="text-left px-4 py-3 font-normal">baseline</th>
            <th className="text-left px-4 py-3 font-normal">candidate</th>
            <th className="text-left px-4 py-3 w-32 font-normal">changed keys</th>
          </tr>
        </thead>
        <tbody>
          {diff.aligned_steps.map((sd, idx) => {
            const isDiverge = idx === diff.first_diverging_step;
            return (
              <tr
                key={idx}
                className={`border-t border-border-1 ${
                  isDiverge ? "bg-signal-failure/[0.05]" : ""
                }`}
              >
                <td className="px-4 py-3 text-text-mute">{String(idx + 1).padStart(3, "0")}</td>
                <td className="px-4 py-3 font-display text-base" style={{ color: KIND_COLOR[sd.kind] }}>
                  {KIND_MARKER[sd.kind]}
                </td>
                <td className="px-4 py-3 text-text-hi">
                  {sd.a ? (
                    <>
                      <div>{payloadBrief(sd.a)}</div>
                      <div className="text-text-mute text-[10px] truncate max-w-md mt-0.5">
                        {responseSummary(sd.a)}
                      </div>
                    </>
                  ) : (
                    <span className="text-text-mute">—</span>
                  )}
                </td>
                <td className="px-4 py-3 text-text-hi">
                  {sd.b ? (
                    <>
                      <div>{payloadBrief(sd.b)}</div>
                      <div className="text-text-mute text-[10px] truncate max-w-md mt-0.5">
                        {responseSummary(sd.b)}
                      </div>
                    </>
                  ) : (
                    <span className="text-text-mute">—</span>
                  )}
                </td>
                <td className="px-4 py-3 text-signal-warning">
                  {sd.changed_keys.length > 0 ? sd.changed_keys.join(", ") : ""}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
