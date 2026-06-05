"use client";

import { motion } from "motion/react";

/**
 * A slow-drifting aurora of three radial gradients. Pure CSS animated via motion — no SVG.
 * Designed for the hero + login surfaces.
 */
export function AuroraBackdrop() {
  return (
    <>
      <motion.div
        aria-hidden
        className="absolute -top-1/3 -left-1/4 w-[80vw] h-[80vw] rounded-full pointer-events-none"
        style={{
          background:
            "radial-gradient(circle, rgba(61,224,184,0.20), transparent 60%)",
          filter: "blur(40px)",
        }}
        animate={{ x: [0, 60, -30, 0], y: [0, -40, 30, 0] }}
        transition={{ duration: 26, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        aria-hidden
        className="absolute -top-1/4 -right-1/4 w-[70vw] h-[70vw] rounded-full pointer-events-none"
        style={{
          background:
            "radial-gradient(circle, rgba(111,170,255,0.22), transparent 60%)",
          filter: "blur(40px)",
        }}
        animate={{ x: [0, -50, 40, 0], y: [0, 30, -20, 0] }}
        transition={{ duration: 30, repeat: Infinity, ease: "easeInOut", delay: 2 }}
      />
      <motion.div
        aria-hidden
        className="absolute -bottom-1/3 left-1/3 w-[60vw] h-[60vw] rounded-full pointer-events-none"
        style={{
          background:
            "radial-gradient(circle, rgba(182,121,255,0.16), transparent 60%)",
          filter: "blur(40px)",
        }}
        animate={{ x: [0, -30, 30, 0], y: [0, 40, -30, 0] }}
        transition={{ duration: 34, repeat: Infinity, ease: "easeInOut", delay: 4 }}
      />
    </>
  );
}
