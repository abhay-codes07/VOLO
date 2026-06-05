"use client";

import { motion } from "motion/react";
import type { Recording, ReportSummary } from "@/lib/api";
import { TrajectoryCanvas } from "@/components/TrajectoryCanvas";
import { MouseSpotlight } from "@/components/motion/MouseSpotlight";
import { MagneticButton } from "@/components/motion/MagneticButton";
import { Tilt } from "@/components/motion/Tilt";
import { AuroraBackdrop } from "@/components/motion/AuroraBackdrop";

/**
 * Anthropic-style editorial hero — serif headline + italic accent — paired with a
 * Linear-style "live monitor" mock on the right showing the actual product surface.
 */
export function Hero({
  baselineRec,
  candidateRec,
  baselineSummary,
  candidateSummary,
  failureIndex,
}: {
  baselineRec: Recording | null;
  candidateRec: Recording | null;
  baselineSummary: ReportSummary | null;
  candidateSummary: ReportSummary | null;
  failureIndex: number | null;
}) {
  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 -z-10 opacity-80">
        <AuroraBackdrop />
      </div>
      <MouseSpotlight color="rgba(61, 224, 184, 0.12)" size={720} />

      <div className="relative max-w-7xl mx-auto px-6 md:px-10 pt-20 pb-24">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-7">
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="chip mb-10"
            >
              <span className="dot-live" /> open-source · pre-alpha · v0.1.0
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.85, ease: [0.16, 1, 0.3, 1] }}
              className="font-serif text-[clamp(3rem,9vw,7rem)] leading-[0.98] tracking-tight text-text-hi mb-10"
              style={{ fontFeatureSettings: '"ss01"' }}
            >
              Mission control
              <br />
              <em className="not-italic font-serif text-text-mid">for </em>
              <em className="font-serif text-signal-nominal">AI agents.</em>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.45, duration: 0.6 }}
              className="text-text-mid text-xl max-w-md leading-relaxed mb-10"
            >
              Record an agent. Replay it against an adversarial simulator. In CI.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.65, duration: 0.6 }}
              className="flex flex-wrap items-center gap-3"
            >
              <MagneticButton href="/auth/login" variant="primary">Open dashboard ↘</MagneticButton>
              <MagneticButton href="https://github.com/volo-sim/volo" variant="secondary" external>★ Star · 0</MagneticButton>
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0, x: 20, scale: 0.97 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            transition={{ delay: 0.3, duration: 0.95, ease: [0.16, 1, 0.3, 1] }}
            className="lg:col-span-5 relative"
          >
            <div
              aria-hidden
              className="absolute -inset-10 rounded-3xl"
              style={{
                background: "radial-gradient(60% 60% at 50% 50%, rgba(61,224,184,0.22), transparent 65%)",
                filter: "blur(28px)",
              }}
            />
            <Tilt className="relative" max={5} glare>
              <div className="hairline bg-surface-1 shadow-elev-2 rounded-md overflow-hidden">
                <div className="flex items-center justify-between px-4 py-2.5 border-b border-border-1 bg-surface-2/40">
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-signal-failure/80" />
                    <span className="w-2.5 h-2.5 rounded-full bg-signal-warning/80" />
                    <span className="w-2.5 h-2.5 rounded-full bg-signal-nominal/80" />
                  </div>
                  <div className="font-mono text-[10px] uppercase tracking-widest text-text-mute">
                    flight-path · live
                  </div>
                  <div className="font-mono text-[10px] text-text-mute">v1 · v2</div>
                </div>
                <div className="p-4 space-y-3">
                  <div className="flex items-center justify-between text-[10px] font-mono text-text-mute uppercase tracking-widest">
                    <span>baseline</span>
                    <span className="chip chip-nominal">{baselineSummary?.verdict?.replace("_", " ") ?? "—"}</span>
                  </div>
                  <TrajectoryCanvas steps={baselineRec?.steps ?? []} height={130} />
                  <div className="etched-divider my-1" />
                  <div className="flex items-center justify-between text-[10px] font-mono text-text-mute uppercase tracking-widest">
                    <span>candidate</span>
                    <span className="chip chip-failure">{candidateSummary?.verdict?.replace("_", " ") ?? "—"}</span>
                  </div>
                  <TrajectoryCanvas steps={candidateRec?.steps ?? []} height={130} failureIndex={failureIndex} />
                </div>
              </div>
            </Tilt>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
