"use client";

import { Marquee } from "@/components/motion/Marquee";
import { CountUp } from "@/components/motion/CountUp";

export function StatsBar({
  recordings, reports, scenarios, steps,
}: {
  recordings: number; reports: number; scenarios: number; steps: number;
}) {
  const cells = [
    { v: recordings, l: "recordings",      tag: "live" },
    { v: reports,    l: "reports",         tag: "live" },
    { v: scenarios,  l: "scenarios",       tag: "ADR-0005" },
    { v: steps,      l: "spans captured",  tag: "schema v1.0.0" },
  ];

  const marqueeTags = [
    "TRAJECTORY DETERMINISM", "DECISION DETERMINISM", "FAITHFULNESS", "CONSISTENCY-UNDER-REPETITION",
    "DROP TOOL RESULT", "CORRUPT FIELD", "INJECT LATENCY", "AMBIGUOUS USER TURN",
    "PROMPT INJECTION", "REORDER STEPS", "LONG HORIZON REPEAT", "GIT BISECT FOR AGENTS",
  ];

  return (
    <section className="relative border-y border-border-1 bg-surface-1">
      <Marquee duration={48}>
        {marqueeTags.map((t, i) => (
          <span key={i} className="font-mono text-[11px] uppercase tracking-widest text-text-mute flex items-center gap-3 whitespace-nowrap">
            <span className="w-1 h-1 rounded-full bg-signal-nominal" />{t}
          </span>
        ))}
      </Marquee>

      <div className="border-t border-border-1">
        <div className="max-w-7xl mx-auto px-6 md:px-10 py-7">
          <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-border-1">
            {cells.map((c, i) => (
              <div key={i} className={`px-6 ${i === 0 ? "pl-0" : ""}`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="dot-live" />
                  <span className="font-mono text-[10px] uppercase tracking-widest text-text-mute">{c.tag}</span>
                </div>
                <div className="font-display text-3xl md:text-4xl font-semibold tracking-tighter text-text-hi tabular">
                  <CountUp to={c.v} />
                </div>
                <div className="font-mono text-[11px] uppercase tracking-widest text-text-lo mt-1">{c.l}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
