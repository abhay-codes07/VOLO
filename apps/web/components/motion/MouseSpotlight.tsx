"use client";

import { motion, useMotionTemplate, useMotionValue } from "motion/react";
import { useEffect, useRef } from "react";

/**
 * A radial gradient that follows the cursor inside its parent container. Used on the hero +
 * heavy panels to give that Linear/Vercel "the surface is alive" feel. Falls back to a static
 * gradient on touch devices.
 */
export function MouseSpotlight({
  className = "",
  color = "rgba(61, 224, 184, 0.18)",
  size = 520,
}: {
  className?: string;
  color?: string;
  size?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const x = useMotionValue(-9999);
  const y = useMotionValue(-9999);

  useEffect(() => {
    const el = ref.current?.parentElement;
    if (!el) return;
    const handle = (e: PointerEvent) => {
      const rect = el.getBoundingClientRect();
      x.set(e.clientX - rect.left);
      y.set(e.clientY - rect.top);
    };
    const leave = () => {
      x.set(-9999);
      y.set(-9999);
    };
    el.addEventListener("pointermove", handle);
    el.addEventListener("pointerleave", leave);
    return () => {
      el.removeEventListener("pointermove", handle);
      el.removeEventListener("pointerleave", leave);
    };
  }, [x, y]);

  const background = useMotionTemplate`radial-gradient(${size}px circle at ${x}px ${y}px, ${color}, transparent 70%)`;

  return (
    <motion.div
      ref={ref}
      aria-hidden
      style={{ background }}
      className={`pointer-events-none absolute inset-0 ${className}`}
    />
  );
}
