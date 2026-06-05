"use client";

import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { Reveal } from "@/components/motion/Reveal";

type Tab = "record" | "run" | "diff";

const SCRIPTS: Record<Tab, { lines: { k: "cmd" | "out" | "ok" | "warn" | "fail"; t: string }[] }> = {
  record: {
    lines: [
      { k: "cmd",  t: "$ uv run volo record examples.calc_agent:run \\" },
      { k: "cmd",  t: "      --input '{\"a\":2,\"b\":3,\"c\":4}'" },
      { k: "out",  t: "  · capturing via proxies (ADR-0004)" },
      { k: "out",  t: "  · 5 steps · 1 decision · 2 model · 2 tool" },
      { k: "ok",   t: "✓ recording → .volo/recordings/calc_v1.json" },
    ],
  },
  run: {
    lines: [
      { k: "cmd",  t: "$ uv run volo run calc_v1.json \\" },
      { k: "cmd",  t: "      --agent examples.calc_agent_v2:run --n 2" },
      { k: "out",  t: "  · Tier-1 replayer · cache hit 4/4" },
      { k: "out",  t: "  · scenarios :: 7 applicable" },
      { k: "out",  t: "    drop_tool_result      ×2" },
      { k: "out",  t: "    corrupt_field         ×2" },
      { k: "out",  t: "    inject_latency        ×2" },
      { k: "out",  t: "    ambiguous_user_turn   ×2" },
      { k: "out",  t: "    prompt_injection      ×2" },
      { k: "out",  t: "    reorder_steps         ×2" },
      { k: "out",  t: "    long_horizon_repeat   ×2" },
      { k: "fail", t: "✗ verdict NO_SHIP · faithfulness 0.000" },
    ],
  },
  diff: {
    lines: [
      { k: "cmd",  t: "$ uv run volo diff calc_v1.json calc_v2.json" },
      { k: "out",  t: "  · LCS aligned" },
      { k: "out",  t: "  [001] = decision    plan_compute" },
      { k: "out",  t: "  [002] = model_call  echo/echo-1" },
      { k: "out",  t: "  [003] = tool_call   add        result=5" },
      { k: "warn", t: "  [004] ~ tool_call   multiply   ← divergence" },
      { k: "out",  t: "  [005] = model_call  echo/echo-1" },
      { k: "fail", t: "✗ first_diverging_step = 3" },
    ],
  },
};

const KIND_COLOR: Record<string, string> = {
  cmd:  "var(--text-hi)",
  out:  "var(--text-lo)",
  ok:   "var(--signal-nominal)",
  warn: "var(--signal-warning)",
  fail: "var(--signal-failure)",
};

const TABS: { key: Tab; label: string; desc: string }[] = [
  { key: "record", label: "01 · record", desc: "capture one run" },
  { key: "run",    label: "02 · run",    desc: "score against storms" },
  { key: "diff",   label: "03 · diff",   desc: "pinpoint the break" },
];

export function TerminalDemo() {
  const [tab, setTab] = useState<Tab>("record");
  const lines = SCRIPTS[tab].lines;

  return (
    <section className="relative max-w-7xl mx-auto px-6 md:px-10 py-28">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
        <Reveal className="lg:col-span-4">
          <div className="chip mb-5">CLI</div>
          <h2 className="font-display text-display-md font-semibold text-text-hi tracking-tighter mb-6">
            Three commands.<br />
            <span className="text-text-mid">That's the loop.</span>
          </h2>
          <div className="space-y-2.5">
            {TABS.map((t) => (
              <motion.button
                key={t.key}
                onClick={() => setTab(t.key)}
                whileHover={{ x: 4 }}
                whileTap={{ scale: 0.98 }}
                transition={{ type: "spring", stiffness: 320, damping: 22 }}
                data-cursor="hover"
                className={`relative w-full text-left hairline px-5 py-4 transition-colors ${
                  tab === t.key ? "bg-surface-2 border-border-3" : "bg-surface-1"
                }`}
              >
                {tab === t.key && (
                  <motion.span
                    layoutId="terminal-active"
                    className="absolute left-0 top-0 bottom-0 w-[2px] bg-signal-nominal"
                    transition={{ type: "spring", stiffness: 380, damping: 28 }}
                  />
                )}
                <div className={`font-mono text-sm uppercase tracking-widest ${tab === t.key ? "text-signal-nominal" : "text-text-lo"}`}>{t.label}</div>
                <div className="text-text-mid text-sm mt-1">{t.desc}</div>
              </motion.button>
            ))}
          </div>
        </Reveal>

        <Reveal delay={0.15} className="lg:col-span-8">
          <div className="relative">
            <div aria-hidden className="absolute -inset-3 rounded-2xl" style={{ background: "radial-gradient(60% 60% at 50% 50%, rgba(111,170,255,0.10), transparent 70%)", filter: "blur(28px)" }} />
            <div className="relative hairline bg-surface-1 shadow-elev-2 rounded-md overflow-hidden">
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-border-1 bg-surface-2/40">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-signal-failure/80" />
                  <span className="w-2.5 h-2.5 rounded-full bg-signal-warning/80" />
                  <span className="w-2.5 h-2.5 rounded-full bg-signal-nominal/80" />
                </div>
                <div className="font-mono text-[10px] uppercase tracking-widest text-text-mute">~/volo — bash · {tab}</div>
                <div className="font-mono text-[10px] text-text-mute">UTF-8</div>
              </div>

              <div className="p-6 font-mono text-[13px] leading-[1.7] min-h-[260px]">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={tab}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
                  >
                    {lines.map((l, i) => (
                      <motion.div
                        key={`${tab}-${i}`}
                        initial={{ opacity: 0, x: -6 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.35, delay: i * 0.055, ease: [0.16, 1, 0.3, 1] }}
                        style={{ color: KIND_COLOR[l.k] }}
                      >
                        {l.t}
                      </motion.div>
                    ))}
                    <div className="text-text-mute mt-1">
                      ${" "}
                      <motion.span animate={{ opacity: [1, 0.1, 1] }} transition={{ duration: 1.2, repeat: Infinity }} className="inline-block w-2 h-3.5 bg-signal-nominal align-middle" />
                    </div>
                  </motion.div>
                </AnimatePresence>
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
