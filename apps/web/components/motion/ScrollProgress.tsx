"use client";

import { motion, useScroll, useSpring } from "motion/react";

export function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const x = useSpring(scrollYProgress, { stiffness: 220, damping: 28, mass: 0.3 });
  return (
    <motion.div
      aria-hidden
      className="fixed top-0 left-0 right-0 h-[2px] z-[60] origin-left"
      style={{
        scaleX: x,
        background:
          "linear-gradient(90deg, var(--signal-info), var(--signal-nominal) 60%, var(--signal-magenta))",
      }}
    />
  );
}
