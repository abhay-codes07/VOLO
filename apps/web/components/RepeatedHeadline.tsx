"use client";

import { motion, useScroll, useTransform } from "motion/react";
import { useRef } from "react";

/**
 * Linear's signature: repeat the same headline three times with progressive emphasis.
 * Each line fades/slides into the next as you scroll past.
 */
export function RepeatedHeadline() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] });

  const o1 = useTransform(scrollYProgress, [0, 0.3, 1], [0.2, 0.45, 0.15]);
  const o2 = useTransform(scrollYProgress, [0, 0.5, 1], [0.15, 0.7, 0.2]);
  const o3 = useTransform(scrollYProgress, [0, 0.7, 1], [0.1, 1, 0.4]);

  const x1 = useTransform(scrollYProgress, [0, 1], ["-3%", "3%"]);
  const x2 = useTransform(scrollYProgress, [0, 1], ["3%", "-3%"]);

  return (
    <section ref={ref} className="relative py-32 overflow-hidden">
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <motion.div
          style={{ opacity: o1, x: x1 }}
          className="font-serif text-[clamp(2.5rem,8vw,7rem)] leading-[0.95] tracking-tight text-text-hi"
        >
          Test agents.
        </motion.div>
        <motion.div
          style={{ opacity: o2, x: x2 }}
          className="font-serif text-[clamp(2.5rem,8vw,7rem)] leading-[0.95] tracking-tight text-text-mid italic"
        >
          Test agents.
        </motion.div>
        <motion.div
          style={{ opacity: o3 }}
          className="font-serif text-[clamp(2.5rem,8vw,7rem)] leading-[0.95] tracking-tight"
        >
          <span className="shimmer-text">Test agents like software.</span>
        </motion.div>
      </div>
    </section>
  );
}
