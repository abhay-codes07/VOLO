"use client";

import Link from "next/link";
import { Tilt } from "@/components/motion/Tilt";
import { Reveal, Stagger, StaggerItem } from "@/components/motion/Reveal";

const SCENARIOS = [
  { name: "drop_tool_result",   icon: "✕", tone: "info" },
  { name: "corrupt_field",      icon: "≠", tone: "info" },
  { name: "inject_latency",     icon: "⏳", tone: "warning" },
  { name: "ambiguous_user_turn",icon: "?", tone: "warning" },
  { name: "prompt_injection",   icon: "☠", tone: "failure" },
  { name: "reorder_steps",      icon: "⇄", tone: "warning" },
  { name: "long_horizon_repeat",icon: "∞", tone: "failure" },
];

const TONE_COLOR: Record<string, string> = {
  info:    "var(--signal-info)",
  warning: "var(--signal-warning)",
  failure: "var(--signal-failure)",
};

const TONE_GLOW: Record<string, string> = {
  info:    "rgba(111,170,255,0.22)",
  warning: "rgba(246,183,60,0.22)",
  failure: "rgba(255,92,108,0.22)",
};

export function ScenariosWall() {
  return (
    <section className="relative max-w-7xl mx-auto px-6 md:px-10 py-24">
      <Reveal className="mb-12">
        <h2 className="font-display text-display-md font-semibold text-text-hi tracking-tighter">
          Seven storms.
        </h2>
      </Reveal>

      <Stagger className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
        {SCENARIOS.map((s, i) => (
          <StaggerItem key={s.name}>
            <Tilt max={8} className="aspect-square">
              <article
                className="group relative h-full hairline bg-surface-1 p-5 overflow-hidden flex flex-col justify-between"
                data-cursor="hover"
              >
                <span
                  aria-hidden
                  style={{ background: `radial-gradient(70% 70% at 50% 30%, ${TONE_GLOW[s.tone]}, transparent 70%)` }}
                  className="absolute inset-0 pointer-events-none opacity-70 group-hover:opacity-100 transition-opacity"
                />
                <div className="relative font-mono text-[10px] uppercase tracking-widest text-text-mute">
                  · 0{i + 1}
                </div>
                <div className="relative">
                  <div className="font-display text-5xl leading-none" style={{ color: TONE_COLOR[s.tone] }} aria-hidden>
                    {s.icon}
                  </div>
                  <div className="font-mono text-[10px] uppercase tracking-widest text-text-lo mt-3 truncate">
                    {s.name.replace(/_/g, " ")}
                  </div>
                </div>
              </article>
            </Tilt>
          </StaggerItem>
        ))}

        <StaggerItem>
          <Tilt max={5} className="aspect-square">
            <Link
              href={"/scenarios" as never}
              data-cursor="hover"
              className="group h-full hairline-2 bg-surface-1 p-5 flex flex-col justify-between hover:border-signal-nominal transition-colors"
            >
              <div className="font-mono text-[10px] uppercase tracking-widest text-text-mute">· 08</div>
              <div>
                <div className="font-display text-3xl font-semibold tracking-tighter text-signal-nominal leading-none">
                  →
                </div>
                <div className="font-mono text-[10px] uppercase tracking-widest text-text-lo mt-3">
                  all storms
                </div>
              </div>
            </Link>
          </Tilt>
        </StaggerItem>
      </Stagger>
    </section>
  );
}
