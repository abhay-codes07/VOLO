"use client";

import { motion } from "motion/react";
import type { Diff, Recording, ReportSummary } from "@/lib/api";
import { TrajectoryCanvas } from "@/components/TrajectoryCanvas";
import { DiffView } from "@/components/DiffView";
import { Reveal } from "@/components/motion/Reveal";
import { MagneticButton } from "@/components/motion/MagneticButton";

export function CaseStudy({
  baselineRec, candidateRec, baselineSummary, candidateSummary, diff,
}: {
  baselineRec: Recording | null;
  candidateRec: Recording | null;
  baselineSummary: ReportSummary | null;
  candidateSummary: ReportSummary | null;
  diff: Diff | null;
}) {
  const failureIndex = diff?.first_diverging_step ?? null;
  return (
    <section className="relative max-w-7xl mx-auto px-6 md:px-10 py-24">
      <Reveal>
        <div className="mb-12 flex items-end justify-between gap-6 flex-wrap">
          <h2 className="font-display text-display-md font-semibold text-text-hi tracking-tighter">
            One off-by-one.<br />
            <span className="text-signal-nominal">Three ms.</span>
          </h2>
          <MagneticButton href="/diff" variant="secondary">diff →</MagneticButton>
        </div>
      </Reveal>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Panel rec={baselineRec} summary={baselineSummary} tone="nominal" delay={0} />
        <Panel rec={candidateRec} summary={candidateSummary} tone={candidateSummary?.verdict === "no_ship" ? "failure" : "nominal"} failureIndex={failureIndex} delay={0.1} />
      </div>

      {diff && (
        <Reveal delay={0.15} className="mt-6">
          <DiffView diff={diff} />
        </Reveal>
      )}
    </section>
  );
}

function Panel({
  rec, summary, tone, failureIndex, delay,
}: {
  rec: Recording | null;
  summary: ReportSummary | null;
  tone: "nominal" | "failure";
  failureIndex?: number | null;
  delay: number;
}) {
  const verdictChip = tone === "failure" ? "chip chip-failure" : "chip chip-nominal";
  return (
    <motion.article
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.8, delay, ease: [0.16, 1, 0.3, 1] }}
      className="hairline bg-surface-1 shadow-elev-1"
    >
      <div className="flex items-center justify-between border-b border-border-1 px-5 py-3">
        <div className="font-mono text-[11px] uppercase tracking-widest text-text-mute truncate">
          {tone === "failure" ? "candidate" : "baseline"}
        </div>
        <div className={verdictChip}>{summary?.verdict?.replace("_", " ") ?? "—"}</div>
      </div>

      <div className="p-5 space-y-4">
        <TrajectoryCanvas steps={rec?.steps ?? []} height={200} failureIndex={failureIndex} />
        <div className="font-mono text-xs text-text-lo">
          → <span className="text-text-hi">{JSON.stringify(rec?.final_output ?? null)}</span>
        </div>
      </div>
    </motion.article>
  );
}
