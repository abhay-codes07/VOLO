"use client";

import { motion } from "motion/react";

/**
 * Infinite-loop marquee strip. Two copies of children render side by side and translate −50%
 * over `duration` seconds.
 */
export function Marquee({
  children,
  duration = 36,
  direction = "left",
  className = "",
}: {
  children: React.ReactNode;
  duration?: number;
  direction?: "left" | "right";
  className?: string;
}) {
  const animateTo = direction === "left" ? ["0%", "-50%"] : ["-50%", "0%"];
  return (
    <div className={`relative overflow-hidden ${className}`}>
      <motion.div
        className="flex shrink-0"
        animate={{ x: animateTo }}
        transition={{ duration, ease: "linear", repeat: Infinity }}
      >
        <div className="flex shrink-0 gap-12 px-6 items-center">{children}</div>
        <div className="flex shrink-0 gap-12 px-6 items-center" aria-hidden>{children}</div>
      </motion.div>
    </div>
  );
}
