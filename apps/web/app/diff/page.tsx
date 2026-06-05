import Link from "next/link";
import { TopNav } from "@/components/TopNav";
import { PageHeader } from "@/components/PageHeader";
import { DiffView } from "@/components/DiffView";
import { TrajectoryCanvas } from "@/components/TrajectoryCanvas";
import { Footer } from "@/components/Footer";
import {
  computeDiff,
  getNamedDiff,
  getRecording,
  listRecordings,
  safe,
} from "@/lib/api";

export default async function DiffPage({
  searchParams,
}: {
  searchParams: Promise<{ a?: string; b?: string }>;
}) {
  const { a, b } = await searchParams;
  const recordings = (await safe(listRecordings())) ?? [];

  const aId = a ?? recordings.find((r) => r.stem === "calc_v1")?.stem ?? recordings[0]?.stem;
  const bId = b ?? recordings.find((r) => r.stem === "calc_v2")?.stem ?? recordings[1]?.stem;

  if (!aId || !bId) {
    return (
      <>
        <TopNav />
        <PageHeader
          eyebrow="DIFF · GIT BISECT FOR AGENTS"
          title="No recordings yet."
          description="Run uv run volo demo to seed showcase data, then come back."
        />
        <Footer />
      </>
    );
  }

  const [recA, recB] = await Promise.all([
    safe(getRecording(aId)),
    safe(getRecording(bId)),
  ]);
  const namedDiff =
    aId === "calc_v1" && bId === "calc_v2"
      ? await safe(getNamedDiff("v1_vs_v2"))
      : null;
  const diff =
    namedDiff ??
    (recA && recB ? await safe(computeDiff(recA.run_id, recB.run_id)) : null);

  const divergent = diff?.first_diverging_step ?? null;

  return (
    <>
      <TopNav />
      <PageHeader
        eyebrow="DIFF · GIT BISECT FOR AGENTS"
        title={
          <>
            Pinpoint the <span className="shimmer-text">breaking step</span>.
          </>
        }
        description={
          diff
            ? diff.first_diverging_step === null
              ? "Trajectories match — no regression detected."
              : `Divergence pinpointed at aligned step #${diff.first_diverging_step}.`
            : "Could not compute diff."
        }
        right={
          divergent !== null && (
            <div className="chip chip-failure">step #{divergent} · divergence</div>
          )
        }
      />

      <main className="max-w-7xl mx-auto px-6 md:px-10 pb-24 space-y-8">
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-widest text-text-mute mb-2">
              baseline · {aId}
            </div>
            <TrajectoryCanvas
              steps={recA?.steps ?? []}
              failureIndex={divergent}
              height={220}
            />
          </div>
          <div>
            <div className="font-mono text-[11px] uppercase tracking-widest text-text-mute mb-2">
              candidate · {bId}
            </div>
            <TrajectoryCanvas
              steps={recB?.steps ?? []}
              failureIndex={divergent}
              height={220}
            />
          </div>
        </section>

        {diff && <DiffView diff={diff} />}

        <section className="hairline bg-surface-1 p-7 shadow-elev-1">
          <div className="font-mono text-[11px] uppercase tracking-widest text-text-mute mb-3">
            switch recordings
          </div>
          <p className="text-text-lo text-sm mb-4">
            Pass <code className="text-signal-info">?a=&lt;stem&gt;&amp;b=&lt;stem&gt;</code> in the URL.
            Available recordings:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {recordings.map((r) => (
              <div key={r.run_id} className="hairline bg-surface-2/40 px-4 py-3 flex items-center justify-between gap-2">
                <span className="font-mono text-xs text-text-hi truncate">{r.stem}</span>
                <div className="flex gap-2 shrink-0">
                  <Link
                    href={`/diff?a=${encodeURIComponent(r.stem)}&b=${encodeURIComponent(bId)}` as never}
                    className="text-[10px] font-mono uppercase tracking-widest text-text-lo hover:text-signal-nominal"
                  >
                    set A
                  </Link>
                  <Link
                    href={`/diff?a=${encodeURIComponent(aId)}&b=${encodeURIComponent(r.stem)}` as never}
                    className="text-[10px] font-mono uppercase tracking-widest text-text-lo hover:text-signal-nominal"
                  >
                    set B
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>

      <Footer />
    </>
  );
}
