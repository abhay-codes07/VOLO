import { TopNav } from "@/components/TopNav";
import { Footer } from "@/components/Footer";
import { PageHeader } from "@/components/PageHeader";
import { Sparkline } from "@/components/Sparkline";
import { getShadowHistory, type ShadowCheck, type CorpusTrace } from "@/lib/shadow";
import type { ReportSummary } from "@/lib/api";

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

export default async function ShadowDashboard() {
  const history = await safe(getShadowHistory());
  const checks: ShadowCheck[] = history?.checks ?? [];
  const corpus: CorpusTrace[] = history?.corpus ?? [];
  const latest = checks.at(-1) ?? null;
  const driftedNights = checks.filter((c) => c.drifted).length;
  // Sparkline only reads `.aggregate[metric]`, which ShadowCheck provides.
  const asReports = checks as unknown as ReportSummary[];

  return (
    <>
      <TopNav />
      <PageHeader
        eyebrow="SHADOW · DRIFT SENTINEL"
        title={
          <>
            Production, replayed <span className="shimmer-text">nightly</span>.
          </>
        }
        description="Every banked production trace, replayed against the current build on every check. A dimension that sinks — or a verdict that flips — pages you before your users notice."
        right={
          <div className="font-mono text-xs uppercase tracking-widest text-text-mute">
            {checks.length} check{checks.length === 1 ? "" : "s"} ·{" "}
            {corpus.length} banked trace{corpus.length === 1 ? "" : "s"}
          </div>
        }
      />

      <main className="max-w-7xl mx-auto px-6 md:px-10 pb-24 space-y-8">
        {checks.length === 0 ? (
          <div
            className="hairline-2 bg-surface-1 p-12 text-center"
            style={{ borderColor: "var(--signal-warning-soft)" }}
          >
            <div className="chip chip-warning mb-4 inline-flex">no shadow history yet</div>
            <p className="text-text-mid">
              Bank traces with <code className="text-signal-info">uv run volo shadow pull</code>,
              then run <code className="text-signal-info">uv run volo shadow check</code> nightly.
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
                      {m.label} · fleet avg
                    </div>
                    <div
                      className="font-display text-4xl font-semibold tabular tracking-tighter mb-4"
                      style={{ color }}
                    >
                      {value !== undefined ? value.toFixed(3) : "—"}
                    </div>
                    <Sparkline reports={asReports} metric={m.key} color={color} />
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
                  checks · newest first
                </div>
                <div className="font-mono text-[11px]" style={{ color: driftedNights ? "var(--signal-failure)" : "var(--text-mute)" }}>
                  {driftedNights} drifted
                </div>
              </div>
              <table className="w-full font-mono text-xs">
                <thead>
                  <tr className="text-text-mute uppercase tracking-widest text-[10px]">
                    <th className="text-left px-5 py-3 font-normal">when</th>
                    <th className="text-left px-5 py-3 font-normal">status</th>
                    <th className="text-right px-3 py-3 font-normal">traces</th>
                    <th className="text-right px-3 py-3 font-normal">findings</th>
                    {METRICS.map((m) => (
                      <th key={m.key} className="text-right px-3 py-3 font-normal">
                        {m.label.split(" ")[0]}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {checks.slice().reverse().map((c, i) => (
                    <tr key={`${c.at ?? "check"}-${i}`} className="border-t border-border-1 hover:bg-surface-2/40 transition-colors">
                      <td className="px-5 py-3 text-text-mute">{c.at ? c.at.slice(0, 19) : "—"}</td>
                      <td className="px-5 py-3">
                        <span className={c.drifted ? "chip chip-failure" : "chip chip-nominal"}>
                          {c.drifted ? "drift" : "quiet"}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-right tabular text-text-mid">{c.traces}</td>
                      <td className="px-3 py-3 text-right tabular" style={{ color: c.findings ? "var(--signal-failure)" : "var(--text-mute)" }}>
                        {c.findings}
                      </td>
                      {METRICS.map((m) => {
                        const v = c.aggregate?.[m.key];
                        return (
                          <td key={m.key} className="px-3 py-3 text-right tabular" style={{ color: statusColor(v) }}>
                            {v !== undefined ? v.toFixed(2) : "—"}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section className="hairline bg-surface-1 shadow-elev-1 overflow-hidden">
              <div className="px-5 py-3 border-b border-border-1 bg-surface-2/40 font-mono text-[11px] uppercase tracking-widest text-text-mute">
                banked corpus
              </div>
              <table className="w-full font-mono text-xs">
                <thead>
                  <tr className="text-text-mute uppercase tracking-widest text-[10px]">
                    <th className="text-left px-5 py-3 font-normal">trace</th>
                    <th className="text-left px-3 py-3 font-normal">source</th>
                    <th className="text-left px-3 py-3 font-normal">agent</th>
                    <th className="text-right px-3 py-3 font-normal">steps</th>
                    <th className="text-right px-5 py-3 font-normal">banked</th>
                  </tr>
                </thead>
                <tbody>
                  {corpus.map((t) => (
                    <tr key={t.run_id} className="border-t border-border-1 hover:bg-surface-2/40 transition-colors">
                      <td className="px-5 py-3 text-text-hi truncate max-w-[18rem]">{t.run_id}</td>
                      <td className="px-3 py-3">
                        <span className={t.source === "incident" ? "chip chip-warning" : "chip"}>
                          {t.source}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-text-mid">{t.agent_name ?? "—"}</td>
                      <td className="px-3 py-3 text-right tabular text-text-mid">{t.steps}</td>
                      <td className="px-5 py-3 text-right text-text-mute">{t.added_at.slice(0, 19)}</td>
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
