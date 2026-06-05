"use client";

import { Tilt } from "@/components/motion/Tilt";
import { Reveal, Stagger, StaggerItem } from "@/components/motion/Reveal";
import { CountUp } from "@/components/motion/CountUp";
import type { ReliabilityReport } from "@/lib/api";

const METRICS = [
  { key: "trajectory_determinism",      label: "Trajectory" },
  { key: "decision_determinism",         label: "Decision" },
  { key: "faithfulness",                 label: "Faithful" },
  { key: "consistency_under_repetition", label: "Consistency" },
] as const;

function statusFor(v: number | undefined) {
  if (v === undefined) return { color: "var(--text-mute)", glow: "transparent" };
  if (v >= 0.9) return { color: "var(--signal-nominal)", glow: "rgba(61,224,184,0.28)" };
  if (v >= 0.6) return { color: "var(--signal-warning)", glow: "rgba(246,183,60,0.28)" };
  return { color: "var(--signal-failure)", glow: "rgba(255,92,108,0.28)" };
}

export function MetricsExplainer({ report }: { report: ReliabilityReport | null }) {
  return (
    <section className="relative max-w-7xl mx-auto px-6 md:px-10 py-24">
      <Reveal className="mb-12">
        <h2 className="font-display text-display-md font-semibold text-text-hi tracking-tighter">
          Four numbers.
        </h2>
      </Reveal>

      <Stagger className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {METRICS.map((m) => {
          const v = report?.aggregate[m.key];
          const s = statusFor(v);
          return (
            <StaggerItem key={m.key}>
              <Tilt max={6} className="h-full">
                <article
                  className="relative h-full hairline bg-surface-1 p-6 shadow-elev-1 overflow-hidden"
                  data-cursor="hover"
                >
                  <span
                    aria-hidden
                    style={{ background: `radial-gradient(60% 60% at 70% 0%, ${s.glow}, transparent 70%)` }}
                    className="absolute inset-0 pointer-events-none"
                  />
                  <div className="relative">
                    <div className="font-mono text-[10px] uppercase tracking-widest text-text-mute mb-6">
                      {m.label}
                    </div>
                    <div className="font-display text-6xl font-semibold tabular tracking-tighter" style={{ color: s.color }}>
                      {v !== undefined ? <CountUp to={v} fractionDigits={3} /> : "—"}
                    </div>
                  </div>
                  <span aria-hidden className="absolute left-0 top-0 bottom-0 w-[2px]" style={{ background: s.color }} />
                </article>
              </Tilt>
            </StaggerItem>
          );
        })}
      </Stagger>
    </section>
  );
}
