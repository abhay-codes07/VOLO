"use client";

import { motion } from "motion/react";
import { Reveal } from "@/components/motion/Reveal";

const NOTES = [
  {
    date: "2026 · 05 · 31",
    tag: "Research",
    title: "Why a single reliability score lies.",
    body: "DFAH proved determinism and accuracy are uncorrelated — collapsing four orthogonal numbers into one hides the failure modes that matter most.",
  },
  {
    date: "2026 · 05 · 30",
    tag: "Engineering",
    title: "The Tier-1 replayer, in 142 lines.",
    body: "Canonical request normalization + content-addressed cache keys + a `ReplayMiss` sentinel that refuses to hallucinate. Deterministic by construction.",
  },
  {
    date: "2026 · 05 · 29",
    tag: "Changelog",
    title: "M1–M4 shipped. 103 tests green.",
    body: "Auto-capture proxies, scenario operators, reliability metrics, step-level diff. Everything traces back to an ADR in the repo.",
  },
];

export function NotesGrid() {
  return (
    <section className="relative max-w-7xl mx-auto px-6 md:px-10 py-28">
      <Reveal className="mb-12 flex items-end justify-between flex-wrap gap-4">
        <h2 className="font-serif text-[clamp(2.5rem,6vw,5rem)] leading-[1] tracking-tight text-text-hi max-w-2xl">
          Notes from <em className="text-signal-nominal">the hangar</em>.
        </h2>
        <a
          href="https://github.com/volo-sim/volo"
          target="_blank"
          rel="noreferrer"
          className="font-mono text-[11px] uppercase tracking-widest text-text-lo hover:text-text-hi"
          data-cursor="hover"
        >
          all entries ↗
        </a>
      </Reveal>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {NOTES.map((n, i) => (
          <motion.article
            key={n.title}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.7, delay: i * 0.1, ease: [0.16, 1, 0.3, 1] }}
            whileHover={{ y: -3 }}
            className="hairline bg-surface-1 shadow-elev-1 p-7 cursor-default"
            data-cursor="hover"
          >
            <div className="flex items-center justify-between mb-6">
              <span className="font-mono text-[10px] uppercase tracking-widest text-text-mute">{n.tag}</span>
              <span className="font-mono text-[10px] text-text-mute tabular">{n.date}</span>
            </div>
            <h3 className="font-serif text-2xl tracking-tight text-text-hi mb-3 leading-snug">
              {n.title}
            </h3>
            <p className="text-text-lo leading-relaxed mb-6">{n.body}</p>
            <span className="font-mono text-[11px] uppercase tracking-widest text-signal-nominal">
              Read →
            </span>
          </motion.article>
        ))}
      </div>
    </section>
  );
}
