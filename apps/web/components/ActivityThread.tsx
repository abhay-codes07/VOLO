"use client";

import { motion } from "motion/react";
import { Reveal } from "@/components/motion/Reveal";

/**
 * Linear's signature "agent activity thread" — embed live agent reasoning + tool calls + outcomes
 * directly into a product surface. Reads like a Slack thread but for the agent.
 */
const EVENTS = [
  { t: "00:00.000", who: "system",     k: "info",  body: "scenario · drop_tool_result · seed 0" },
  { t: "00:00.012", who: "agent",      k: "model", body: "plan: compute (2+3)*4 → call add(2,3) then multiply(_,4)" },
  { t: "00:00.084", who: "tool · add", k: "tool",  body: "{ \"a\": 2, \"b\": 3 } → { \"result\": 5 }" },
  { t: "00:00.131", who: "scenario",   k: "warn",  body: "DROP tool_result on multiply — response replaced with {}" },
  { t: "00:00.142", who: "tool · multiply", k: "tool", body: "{ \"a\": 5, \"b\": 4 } → { }  ← empty" },
  { t: "00:00.198", who: "agent",      k: "model", body: "summary: answer is 20  ← unfaithful (no evidence)" },
  { t: "00:00.220", who: "judge",      k: "fail",  body: "faithfulness = 0.00 · output not grounded in tool returns" },
  { t: "00:00.234", who: "verdict",    k: "fail",  body: "NO_SHIP — reliability regressed below 0.9 floor" },
];

const KIND_COLOR: Record<string, string> = {
  info:  "var(--text-lo)",
  model: "var(--signal-info)",
  tool:  "var(--signal-nominal)",
  warn:  "var(--signal-warning)",
  fail:  "var(--signal-failure)",
};

export function ActivityThread() {
  return (
    <section className="relative max-w-7xl mx-auto px-6 md:px-10 py-28">
      <Reveal className="mb-12 max-w-2xl">
        <div className="chip chip-info mb-5">activity thread</div>
        <h2 className="font-serif text-[clamp(2.5rem,6vw,5rem)] leading-[1] tracking-tight text-text-hi">
          Every <em className="text-signal-nominal">decision</em>. Every tool call. Pinpointed.
        </h2>
      </Reveal>

      <Reveal delay={0.1}>
        <div className="hairline bg-surface-1 shadow-elev-2 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3 border-b border-border-1 bg-surface-2/40">
            <div className="flex items-center gap-3">
              <span className="dot-live" />
              <span className="font-mono text-[11px] uppercase tracking-widest text-text-mute">
                examples.calc_agent_v2:run · scenario 01 · run 1 of 2
              </span>
            </div>
            <div className="chip chip-failure">no_ship</div>
          </div>

          <ol className="divide-y divide-border-1">
            {EVENTS.map((e, i) => (
              <motion.li
                key={i}
                initial={{ opacity: 0, x: -10 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-30px" }}
                transition={{ duration: 0.5, delay: 0.05 + i * 0.08, ease: [0.16, 1, 0.3, 1] }}
                className="grid grid-cols-[88px_140px_1fr] gap-4 items-baseline px-5 py-3 font-mono text-[12px] hover:bg-surface-2/40 transition-colors"
                data-cursor="hover"
              >
                <span className="text-text-mute tabular">{e.t}</span>
                <span
                  className="uppercase tracking-widest text-[10px]"
                  style={{ color: KIND_COLOR[e.k] }}
                >
                  {e.who}
                </span>
                <span className="text-text-hi truncate">{e.body}</span>
              </motion.li>
            ))}
          </ol>

          <div className="border-t border-border-1 bg-surface-2/40 px-5 py-3 flex items-center justify-between font-mono text-[10px] uppercase tracking-widest text-text-mute">
            <span>· 8 events · 0.234 s wall</span>
            <span>step #3 · multiply · divergence</span>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
