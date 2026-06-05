import Link from "next/link";
import { notFound } from "next/navigation";
import { TopNav } from "@/components/TopNav";
import { Footer } from "@/components/Footer";
import { TrajectoryCanvas } from "@/components/TrajectoryCanvas";
import { ReliabilityHeatmap } from "@/components/ReliabilityHeatmap";
import { getRecording, getReport, safe } from "@/lib/api";

export default async function RunPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  const id = decodeURIComponent(runId);
  const recording = await safe(getRecording(id));
  if (!recording) notFound();
  const report = await safe(getReport(id));

  const verdictChip =
    report?.verdict === "ship"
      ? "chip chip-nominal"
      : report?.verdict === "no_ship"
      ? "chip chip-failure"
      : "chip";

  return (
    <>
      <TopNav />

      <section className="relative overflow-hidden">
        <div className="hero-mesh" aria-hidden />
        <div className="hero-noise" aria-hidden />
        <div className="relative max-w-7xl mx-auto px-6 md:px-10 pt-12 pb-10">
          <Link href="/runs" className="font-mono text-[11px] uppercase tracking-widest text-text-mute hover:text-text-hi inline-flex items-center gap-1.5 mb-6">
            ← all runs
          </Link>
          <div className="flex items-end justify-between gap-6 flex-wrap">
            <div>
              <div className="chip mb-4">RUN · {recording!.agent_meta.framework}</div>
              <h1 className="font-display text-display-md font-semibold text-text-hi tracking-tighter truncate max-w-3xl">
                {recording!.agent_meta.agent_name ?? "<unnamed agent>"}
              </h1>
            </div>
            <div className="flex items-center gap-3">
              {report && <div className={verdictChip}>verdict {report.verdict.replace("_", " ")}</div>}
              <div className="chip">schema {recording!.recording_schema_version}</div>
            </div>
          </div>
        </div>
      </section>

      <main className="max-w-7xl mx-auto px-6 md:px-10 pb-24 space-y-8">
        {/* meta strip */}
        <section className="hairline bg-surface-1 shadow-elev-1">
          <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-border-1">
            {[
              { l: "run_id",       v: recording!.run_id.slice(-12),         m: "tabular" },
              { l: "framework",    v: recording!.agent_meta.framework,       m: "" },
              { l: "steps",        v: String(recording!.steps.length),       m: "tabular text-signal-nominal" },
              { l: "redaction",    v: "applied",                              m: "text-signal-info" },
            ].map((c) => (
              <div key={c.l} className="px-6 py-5">
                <div className="font-mono text-[10px] uppercase tracking-widest text-text-mute mb-1">
                  {c.l}
                </div>
                <div className={`font-display text-2xl font-semibold tracking-tighter ${c.m}`}>
                  {c.v}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-display text-xl font-semibold text-text-hi tracking-tight">
              flight path
            </h2>
            <div className="font-mono text-[11px] uppercase tracking-widest text-text-mute">
              {recording!.steps.length} captured spans
            </div>
          </div>
          <TrajectoryCanvas steps={recording!.steps} />
        </section>

        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="hairline bg-surface-1 shadow-elev-1 overflow-hidden">
            <div className="px-5 py-3 border-b border-border-1 bg-surface-2/40 font-mono text-[11px] uppercase tracking-widest text-text-mute">
              final output
            </div>
            <pre className="p-6 font-mono text-sm text-text-hi overflow-x-auto whitespace-pre-wrap">
{JSON.stringify(recording!.final_output, null, 2)}
            </pre>
          </div>
          <div className="hairline bg-surface-1 shadow-elev-1 overflow-hidden">
            <div className="px-5 py-3 border-b border-border-1 bg-surface-2/40 font-mono text-[11px] uppercase tracking-widest text-text-mute">
              agent metadata
            </div>
            <pre className="p-6 font-mono text-sm text-text-hi overflow-x-auto whitespace-pre-wrap">
{JSON.stringify(recording!.agent_meta, null, 2)}
            </pre>
          </div>
        </section>

        {report && (
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-display text-xl font-semibold text-text-hi tracking-tight">
                reliability surface
              </h2>
              <div className="font-mono text-[11px] uppercase tracking-widest text-text-mute">
                7 scenarios × 4 metrics
              </div>
            </div>
            <ReliabilityHeatmap report={report} />
          </section>
        )}
      </main>

      <Footer />
    </>
  );
}
