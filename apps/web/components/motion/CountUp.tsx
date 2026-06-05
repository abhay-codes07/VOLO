"use client";

import { animate, useInView, useMotionValue, useTransform } from "motion/react";
import { motion } from "motion/react";
import { useEffect, useRef } from "react";

export function CountUp({
  to,
  duration = 1.4,
  prefix = "",
  suffix = "",
  fractionDigits = 0,
  className = "",
}: {
  to: number;
  duration?: number;
  prefix?: string;
  suffix?: string;
  fractionDigits?: number;
  className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const v = useMotionValue(0);
  const text = useTransform(v, (latest) =>
    `${prefix}${Number.isFinite(latest) ? latest.toFixed(fractionDigits) : "0"}${suffix}`,
  );

  useEffect(() => {
    if (inView) {
      const controls = animate(v, to, { duration, ease: [0.16, 1, 0.3, 1] });
      return () => controls.stop();
    }
  }, [inView, to, duration, v]);

  return (
    <motion.span ref={ref} className={className}>
      {text}
    </motion.span>
  );
}
