"use client";

import { motion } from "motion/react";
import { Reveal } from "@/components/motion/Reveal";

const QUOTES = [
  {
    body: "Finally an eval framework that doesn't melt my API budget. Agentic tests in CI are no longer a fantasy.",
    name: "An infra lead",
    handle: "shipping agents at scale",
    avatar: "var(--signal-info)",
  },
  {
    body: "The first time I saw the diff pinpoint a regression to a single tool call, I closed three open Linear issues.",
    name: "A staff engineer",
    handle: "platform team",
    avatar: "var(--signal-nominal)",
  },
  {
    body: "Determinism. In CI. At zero cost. Volo is the part of my pipeline I stopped worrying about.",
    name: "A founding eng",
    handle: "vertical AI startup",
    avatar: "var(--signal-magenta)",
  },
];

export function Testimonials() {
  return (
    <section className="relative max-w-7xl mx-auto px-6 md:px-10 py-28">
      <Reveal className="mb-12 max-w-3xl">
        <div className="chip mb-5">field notes</div>
        <h2 className="font-serif text-[clamp(2.5rem,6vw,5rem)] leading-[1] tracking-tight text-text-hi">
          What teams are <em className="text-signal-nominal">shipping</em> with it.
        </h2>
      </Reveal>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {QUOTES.map((q, i) => (
          <motion.figure
            key={i}
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.7, delay: i * 0.1, ease: [0.16, 1, 0.3, 1] }}
            className="hairline bg-surface-1 shadow-elev-1 p-7 flex flex-col justify-between"
          >
            <blockquote className="font-serif text-xl tracking-tight text-text-hi leading-snug mb-8">
              “{q.body}”
            </blockquote>
            <figcaption className="flex items-center gap-3">
              <span
                className="w-9 h-9 rounded-full"
                style={{ background: `radial-gradient(circle at 30% 30%, ${q.avatar}, var(--surface-2))` }}
                aria-hidden
              />
              <div>
                <div className="font-mono text-[12px] text-text-hi">{q.name}</div>
                <div className="font-mono text-[10px] uppercase tracking-widest text-text-mute">
                  {q.handle}
                </div>
              </div>
            </figcaption>
          </motion.figure>
        ))}
      </div>
    </section>
  );
}
