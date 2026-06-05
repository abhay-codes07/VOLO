"use client";

import { Reveal } from "@/components/motion/Reveal";

const ITEMS = [
  { k: "01", v: "Record" },
  { k: "02", v: "Mutate" },
  { k: "03", v: "Replay" },
  { k: "04", v: "Score" },
  { k: "05", v: "Ship" },
];

export function ValueStrip() {
  return (
    <section className="relative max-w-7xl mx-auto px-6 md:px-10 py-20">
      <Reveal>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-px bg-border-1">
          {ITEMS.map((it) => (
            <div key={it.k} className="bg-surface-1 px-5 py-7 hover:bg-surface-2 transition-colors">
              <div className="font-mono text-[10px] uppercase tracking-widest text-text-mute mb-3">
                · {it.k}
              </div>
              <div className="font-display text-3xl font-semibold tracking-tighter text-text-hi">
                {it.v}
              </div>
            </div>
          ))}
        </div>
      </Reveal>
    </section>
  );
}
