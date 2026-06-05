"use client";

import { motion } from "motion/react";
import { Reveal } from "@/components/motion/Reveal";

const CHECKS = [
  { name: "python · lint + typecheck + test", status: "pass", ms: 3210 },
  { name: "web · typecheck",                    status: "pass", ms: 4180 },
  { name: "volo-selfcheck · scenarios",    status: "fail", ms: 12450 },
];

const STATUS = {
  pass: { color: "var(--signal-nominal)", icon: "✓", label: "passed" },
  fail: { color: "var(--signal-failure)", icon: "✗", label: "failed" },
} as const;

export function CISection() {
  return (
    <section className="relative max-w-7xl mx-auto px-6 md:px-10 py-28">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
        <Reveal className="lg:col-span-5">
          <div className="chip chip-info mb-5">CI · GitHub Actions</div>
          <h2 className="font-display text-display-md font-semibold text-text-hi tracking-tighter mb-6">
            Block PRs the way<br />
            you block <span className="text-signal-info">failing tests</span>.
          </h2>
          <ul className="space-y-2.5 text-text-mid">
            {[
              "Deterministic — same seed, same verdict.",
              "Cheap — replays, no live API.",
              "Attributable — step + commit, pinpointed.",
            ].map((l) => (
              <li key={l} className="flex items-start gap-2.5">
                <span className="mt-2 inline-block w-1 h-1 rounded-full bg-signal-nominal" />
                <span>{l}</span>
              </li>
            ))}
          </ul>
        </Reveal>

        <Reveal delay={0.12} className="lg:col-span-7">
          <div className="hairline bg-surface-1 shadow-elev-2 rounded-md overflow-hidden">
            <div className="px-5 py-3 border-b border-border-1 bg-surface-2/40 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="font-mono text-[11px] text-text-lo">volo/volo</span>
                <span className="font-mono text-[11px] text-text-mute">#42</span>
              </div>
              <div className="chip chip-failure">checks failed</div>
            </div>

            <ul>
              {CHECKS.map((c, i) => {
                const s = STATUS[c.status as keyof typeof STATUS];
                return (
                  <motion.li
                    key={c.name}
                    initial={{ opacity: 0, x: -10 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true, margin: "-30px" }}
                    transition={{ duration: 0.5, delay: 0.12 + i * 0.18, ease: [0.16, 1, 0.3, 1] }}
                    className={`flex items-center gap-4 px-5 py-4 ${i < CHECKS.length - 1 ? "border-b border-border-1" : ""}`}
                  >
                    <motion.span
                      initial={{ scale: 0 }}
                      whileInView={{ scale: 1 }}
                      viewport={{ once: true, margin: "-30px" }}
                      transition={{ type: "spring", stiffness: 340, damping: 18, delay: 0.4 + i * 0.18 }}
                      className="font-display text-xl leading-none"
                      style={{ color: s.color }}
                    >
                      {s.icon}
                    </motion.span>
                    <div className="flex-1 min-w-0">
                      <div className="font-mono text-sm text-text-hi truncate">{c.name}</div>
                      <div className="font-mono text-[11px] text-text-mute mt-0.5">{s.label} · {c.ms.toLocaleString()} ms</div>
                    </div>
                  </motion.li>
                );
              })}
            </ul>

            <div className="border-t border-border-2 bg-surface-2/40 px-5 py-4 font-mono text-[12px] text-text-mid">
              <span className="text-signal-failure">volo-bot</span>: <span className="text-text-hi">reliability regressed below 0.9.</span> first diverging step <span className="text-signal-warning">#3</span> · tool <span className="text-signal-warning">multiply</span> · <span className="text-text-mute">blocking merge.</span>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
