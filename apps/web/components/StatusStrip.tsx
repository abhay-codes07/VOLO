"use client";

import { motion } from "motion/react";

export function StatusStrip({
  recordings,
  verdict,
}: {
  recordings: number;
  verdict: "ship" | "no_ship" | null;
}) {
  const v = verdict?.replace("_", " ") ?? "—";
  const tone =
    verdict === "ship"   ? "text-signal-nominal" :
    verdict === "no_ship" ? "text-signal-failure" : "text-text-mute";
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 1.2 }}
      className="border-b border-border-1 bg-surface-0/80 backdrop-blur-md"
    >
      <div className="max-w-7xl mx-auto px-6 md:px-10 h-7 flex items-center justify-between font-mono text-[10px] uppercase tracking-widest text-text-mute">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="dot-live" /> live
          </span>
          <span className="hidden sm:inline">·</span>
          <span className="hidden sm:inline">{recordings} recording{recordings === 1 ? "" : "s"}</span>
          <span className="hidden sm:inline">·</span>
          <span className="hidden sm:inline">calc_v2</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="hidden md:inline">tier-1 replayer · cache hit 4/4</span>
          <span>·</span>
          <span className={tone}>verdict {v}</span>
        </div>
      </div>
    </motion.div>
  );
}
