"use client";

import Link from "next/link";
import { Marquee } from "@/components/motion/Marquee";

export function Footer() {
  return (
    <footer className="relative mt-20 border-t border-border-1 bg-surface-1">
      <Marquee duration={60} className="py-5 border-b border-border-1">
        {[
          "RECORD",
          "REPLAY",
          "SCORE",
          "GATE",
          "SHIP",
          "RECORD",
          "REPLAY",
          "SCORE",
        ].map((t, i) => (
          <span
            key={i}
            className="font-display text-4xl tracking-tightest text-text-mute uppercase whitespace-nowrap flex items-center gap-6"
          >
            <span className="w-2 h-2 rounded-full bg-signal-nominal" />
            {t}
          </span>
        ))}
      </Marquee>

      <div className="max-w-7xl mx-auto px-6 md:px-10 py-12 flex items-center justify-between flex-wrap gap-6">
        <div className="flex items-center gap-2.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-signal-nominal shadow-glow-nominal" />
          <span className="font-display text-lg font-semibold tracking-tighter text-text-hi">
            Volo
          </span>
          <span className="font-mono text-[11px] text-text-mute uppercase tracking-widest ml-2">
            · Apache-2.0
          </span>
        </div>

        <nav className="flex items-center gap-5 font-mono text-[11px] uppercase tracking-widest text-text-lo">
          <Link href="/runs" className="hover:text-text-hi transition-colors">Runs</Link>
          <Link href="/scenarios" className="hover:text-text-hi transition-colors">Scenarios</Link>
          <Link href="/diff" className="hover:text-text-hi transition-colors">Diff</Link>
          <a href="http://localhost:8080/docs" target="_blank" rel="noreferrer" className="hover:text-text-hi transition-colors">API ↗</a>
          <a href="https://github.com/volo-sim/volo" target="_blank" rel="noreferrer" className="hover:text-text-hi transition-colors">GitHub ↗</a>
        </nav>
      </div>
    </footer>
  );
}
