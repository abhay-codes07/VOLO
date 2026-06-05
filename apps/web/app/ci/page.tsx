import Link from "next/link";
import { TopNav } from "@/components/TopNav";
import { Footer } from "@/components/Footer";
import { PageHeader } from "@/components/PageHeader";
import { Sparkline } from "@/components/Sparkline";
import { listCIReports, type CIReport } from "@/lib/ci";

const METRICS = [
  { key: "trajectory_determinism",       label: "Trajectory determinism" },
  { key: "decision_determinism",         label: "Decision determinism" },
  { key: "faithfulness",                 label: "Faithfulness" },
  { key: "consistency_under_repetition", label: "Consistency-under-repetition" },
] as const;

async function safe<T>(p: Promise<T>): Promise<T | null> {
  try { return await p; } catch { return null; }
}

function statusColor(v: number | undefined): string {
  if (v === undefined) return "var(--text-mute)";
  if (v >= 0.9) return "var(--signal-nominal)";
  if (v >= 0.6) return "var(--signal-warning)";
  return "var(--signal-failure)";
}

export default async function CIDashboard() {
  const reports = (await safe(listCIReports())) ?? [];
  const latest = reports.at(-1) ?? null;

  return (
    <>
      <TopNav />
      <PageHeader
        eyebrow="CI · TREND"
        title={
          <>
            Reliability over <span className="shimmer-text">time</span>.
          </>
        }
        description="Every reliability report ever recorded, plotted by metric. Red marks where the run dropped below the 0.9 ship floor."
        right={
          <div className="font-mono text-xs uppercase tracking-widest text-text-mute">
            {reports.length} report{reports.length === 1 ? "" : "s"}
          </div>
        }
      />

      <main className="max-w-7xl mx-auto px-6 md:px-10 pb-24 space-y-8">
        {reports.length === 0 ? (
          <div
            className="hairline-2 bg-surface-1 p-12 text-center"
            style={{ borderColor: "var(--signal-warning-soft)" }}
          >
            <div className="chip chip-warning mb-4 inline-flex">no reports yet</div>
            <p className="text-text-mid">
              Run <code className="text-signal-info">uv run volo demo</code> or{" "}
              <code className="text-signal-info">uv run volo run</code> to populate.
            </p>
          </div>
        ) : (
          <>
            <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {METRICS.map((m) => {
                const value = latest?.aggregate?.[m.key];
                const color = statusColor(value);
                return (
                  <article
                    key={m.key}
                    className="relative hairline bg-surface-1 shadow-elev-1 p-6 overflow-hidden"
                    data-cursor="hover"
                  >
                    <div className="font-mono text-[10px] uppercase tracking-widest text-text-mute mb-2">
                      {m.label}
                    </div>
                    <div
                      className="font-display text-4xl font-semibold tabular tracking-tighter mb-4"
                      style={{ color }}
                    >
                      {value !== undefined ? value.toFixed(3) : "—"}
                    </div>
                    <Sparkline reports={reports} metric={m.key} color={color} />
                    <span
                      aria-hidden
                      className="absolute left-0 top-0 bottom-0 w-[2px]"
                      style={{ background: color }}
                    />
                  </article>
                );
              })}
            </section>

            <section className="hairline bg-surface-1 shadow-elev-1 overflow-hidden">
              <div className="flex items-center justify-between px-5 py-3 border-b border-border-1 bg-surface-2/40">
                <div className="font-mono text-[11px] uppercase tracking-widest text-text-mute">
                  history · sorted by report time
                </div>
                <div className="font-mono text-[11px] text-text-mute">
                  {reports.length} entries
                </div>
              </div>
              <table className="w-full font-mono text-xs">
                <thead>
                  <tr className="text-text-mute uppercase tracking-widest text-[10px]">
                    <th className="text-left px-5 py-3 font-normal">when</th>
                    <th className="text-left px-5 py-3 font-normal">agent</th>
                    <th className="text-left px-5 py-3 font-normal">verdict</th>
                    {METRICS.map((m) => (
                      <th key={m.key} className="text-right px-3 py-3 font-normal">
                        {m.label.split(" ")[0]}
                      </th>
                    ))}
                    <th className="text-right px-5 py-3 font-normal">link</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.slice().reverse().map((r: CIReport) => (
                    <tr key={r.baseline_run_id} className="border-t border-border-1 hover:bg-surface-2/40 transition-colors">
                      <td className="px-5 py-3 text-text-mute">{r.created_at ? r.created_at.slice(0, 19) : "—"}</td>
                      <td className="px-5 py-3 text-text-hi truncate max-w-[14rem]">{r.agent_name ?? r.stem}</td>
                      <td className="px-5 py-3">
                        <span
                          className={r.verdict === "ship" ? "chip chip-nominal" : "chip chip-failure"}
                        >
                          {r.verdict.replace("_", " ")}
                        </span>
                      </td>
                      {METRICS.map((m) => {
                        const v = r.aggregate?.[m.key];
                        return (
                          <td key={m.key} className="px-3 py-3 text-right tabular" style={{ color: statusColor(v) }}>
                            {v !== undefined ? v.toFixed(2) : "—"}
                          </td>
                        );
                      })}
                      <td className="px-5 py-3 text-right">
                        <Link
                          href={`/runs/${encodeURIComponent(r.stem || r.baseline_run_id)}` as never}
                          className="text-text-lo hover:text-signal-info text-[11px] uppercase tracking-widest"
                        >
                          run →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </>
        )}
      </main>
      <Footer />
    </>
  );
}
