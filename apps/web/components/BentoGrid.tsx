"use client";

import Link from "next/link";
import { motion } from "motion/react";
import type { ReliabilityReport } from "@/lib/api";
import { CountUp } from "@/components/motion/CountUp";
import { Reveal } from "@/components/motion/Reveal";
import { ReliabilitySurface3D } from "@/components/ReliabilitySurface3D";

const SCEN = [
  { icon: "✕", c: "var(--signal-info)" },
  { icon: "≠", c: "var(--signal-info)" },
  { icon: "⏳", c: "var(--signal-warning)" },
  { icon: "?", c: "var(--signal-warning)" },
  { icon: "☠", c: "var(--signal-failure)" },
  { icon: "⇄", c: "var(--signal-warning)" },
  { icon: "∞", c: "var(--signal-failure)" },
];

const METRICS = [
  { k: "trajectory_determinism", l: "Trajectory" },
  { k: "decision_determinism",    l: "Decision" },
  { k: "faithfulness",            l: "Faithful" },
  { k: "consistency_under_repetition", l: "Consistency" },
] as const;

function color(v: number | undefined) {
  if (v === undefined) return "var(--text-mute)";
  if (v >= 0.9) return "var(--signal-nominal)";
  if (v >= 0.6) return "var(--signal-warning)";
  return "var(--signal-failure)";
}

export function BentoGrid({ report }: { report: ReliabilityReport | null }) {
  return (
    <section className="relative max-w-7xl mx-auto px-6 md:px-10 py-24">
      <Reveal className="mb-12 max-w-2xl">
        <div className="chip mb-5">the whole product</div>
        <h2 className="font-serif text-[clamp(2.5rem,6vw,5rem)] leading-[1] tracking-tight text-text-hi">
          One <em className="text-signal-nominal">surface</em>. Everything that matters.
        </h2>
      </Reveal>

      <div className="grid grid-cols-1 md:grid-cols-6 gap-3 auto-rows-[minmax(180px,auto)]">
        {/* TILE — 3D SURFACE (large, spans 4 cols × 2 rows) */}
        <Tile className="md:col-span-4 md:row-span-2 p-0 overflow-hidden">
          <div className="px-6 pt-6 pb-3">
            <div className="font-mono text-[10px] uppercase tracking-widest text-text-mute mb-1">01 · isometric surface</div>
            <div className="font-display text-2xl font-semibold tracking-tighter text-text-hi">Reliability, in 3D.</div>
          </div>
          <div className="px-3 pb-3">
            <ReliabilitySurface3D report={report} />
          </div>
        </Tile>

        {/* TILE — metric cluster (2 cols × 1 row) */}
        <Tile className="md:col-span-2 md:row-span-1">
          <div className="font-mono text-[10px] uppercase tracking-widest text-text-mute mb-3">02 · DFAH</div>
          <div className="grid grid-cols-2 gap-3">
            {METRICS.map((m) => {
              const v = report?.aggregate[m.k];
              const c = color(v);
              return (
                <div key={m.k}>
                  <div className="font-mono text-[9px] uppercase tracking-widest text-text-mute mb-1">
                    {m.l}
                  </div>
                  <div className="font-display text-2xl font-semibold tabular tracking-tighter" style={{ color: c }}>
                    {v !== undefined ? <CountUp to={v} fractionDigits={2} /> : "—"}
                  </div>
                </div>
              );
            })}
          </div>
        </Tile>

        {/* TILE — verdict callout (2 × 1) */}
        <Tile className="md:col-span-2 md:row-span-1 group relative overflow-hidden">
          <div className="font-mono text-[10px] uppercase tracking-widest text-text-mute mb-2">03 · verdict</div>
          <div className="font-serif text-5xl text-signal-failure italic leading-none">no_ship</div>
          <div className="font-mono text-[11px] text-text-lo mt-3">faithfulness 0.000 · regression caught</div>
          <span
            aria-hidden
            className="absolute -right-10 -bottom-10 w-40 h-40 rounded-full pointer-events-none"
            style={{ background: "radial-gradient(circle, rgba(255,92,108,0.22), transparent 60%)", filter: "blur(20px)" }}
          />
        </Tile>

        {/* TILE — scenarios sigil (3 × 1) */}
        <Tile className="md:col-span-3 md:row-span-1">
          <div className="font-mono text-[10px] uppercase tracking-widest text-text-mute mb-3">04 · seven storms</div>
          <div className="grid grid-cols-7 gap-2">
            {SCEN.map((s, i) => (
              <motion.div
                key={i}
                whileHover={{ scale: 1.15, y: -2 }}
                transition={{ type: "spring", stiffness: 320, damping: 18 }}
                className="aspect-square hairline flex items-center justify-center font-display text-2xl"
                style={{ color: s.c }}
                data-cursor="hover"
              >
                {s.icon}
              </motion.div>
            ))}
          </div>
          <Link href="/scenarios" className="font-mono text-[10px] uppercase tracking-widest text-signal-nominal mt-4 inline-block hover:translate-x-1 transition-transform">
            open library →
          </Link>
        </Tile>

        {/* TILE — diff teaser (3 × 1) */}
        <Tile className="md:col-span-3 md:row-span-1 relative overflow-hidden">
          <div className="font-mono text-[10px] uppercase tracking-widest text-text-mute mb-3">05 · git bisect for agents</div>
          <pre className="font-mono text-[11px] leading-relaxed text-text-lo overflow-hidden">
{`  [001] = decision    plan_compute
  [002] = model_call  echo/echo-1
  [003] = tool_call   add        result=5
  [004] `}<span className="text-signal-warning">{`~ tool_call   multiply   ← divergence`}</span>{`
  [005] = model_call  echo/echo-1`}
          </pre>
          <div className="font-mono text-[10px] text-signal-failure mt-3">
            first_diverging_step = 3
          </div>
        </Tile>
      </div>
    </section>
  );
}

function Tile({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
      className={`hairline bg-surface-1 p-6 shadow-elev-1 ${className}`}
    >
      {children}
    </motion.div>
  );
}
