import Link from "next/link";
import { TopNav } from "@/components/TopNav";
import { PageHeader } from "@/components/PageHeader";
import { Footer } from "@/components/Footer";
import { listRecordings, safe } from "@/lib/api";

export default async function RunsPage() {
  const recordings = (await safe(listRecordings())) ?? [];

  return (
    <>
      <TopNav />
      <PageHeader
        eyebrow="RECORDED RUNS"
        title={
          <>
            Every flight in <span className="shimmer-text">the hangar</span>.
          </>
        }
        description="Each row is a captured agent trajectory — versioned, redacted, and ready to replay against the adversarial simulator."
      />

      <main className="max-w-7xl mx-auto px-6 md:px-10 pb-24">
        {recordings.length === 0 ? (
          <div className="hairline-2 bg-surface-1 p-12 text-center" style={{ borderColor: "var(--signal-warning-soft)" }}>
            <div className="chip chip-warning mb-4 inline-flex">no recordings yet</div>
            <p className="text-text-mid mb-2">
              Seed the showcase data with:
            </p>
            <code className="font-mono text-signal-info">uv run volo demo</code>
          </div>
        ) : (
          <div className="hairline bg-surface-1 shadow-elev-1 overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b border-border-1 bg-surface-2/40">
              <div className="font-mono text-[11px] uppercase tracking-widest text-text-mute">
                {recordings.length} recording{recordings.length === 1 ? "" : "s"} · sorted by stem
              </div>
              <div className="font-mono text-[11px] text-text-mute">schema v1.0.0</div>
            </div>
            <table className="w-full">
              <thead>
                <tr className="text-text-mute uppercase tracking-widest text-[10px] font-mono border-b border-border-1">
                  <th className="text-left px-6 py-3 font-normal">agent</th>
                  <th className="text-left px-6 py-3 font-normal">framework</th>
                  <th className="text-right px-6 py-3 font-normal">steps</th>
                  <th className="text-left px-6 py-3 font-normal">final output</th>
                  <th className="text-right px-6 py-3 font-normal">run_id</th>
                </tr>
              </thead>
              <tbody>
                {recordings.map((r, i) => (
                  <tr key={r.run_id} className={`group hover:bg-surface-2/40 transition-colors ${i > 0 ? "border-t border-border-1" : ""}`}>
                    <td className="px-6 py-4">
                      <Link
                        href={`/runs/${encodeURIComponent(r.stem || r.run_id)}` as never}
                        className="text-text-hi font-mono text-sm hover:text-signal-nominal flex items-center gap-2"
                      >
                        <span className="text-text-mute group-hover:text-signal-nominal transition-colors">▸</span>
                        {r.agent_name ?? r.stem}
                      </Link>
                    </td>
                    <td className="px-6 py-4 font-mono text-sm text-text-lo">
                      {r.framework}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className="font-display text-lg tabular tracking-tighter text-signal-nominal">
                        {r.n_steps}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-text-mid truncate max-w-xs">
                      {JSON.stringify(r.final_output)}
                    </td>
                    <td className="px-6 py-4 font-mono text-[10px] text-text-mute text-right truncate">
                      {r.run_id.slice(-12)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      <Footer />
    </>
  );
}
