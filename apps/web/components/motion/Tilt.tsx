"use client";

import { motion, useMotionValue, useSpring, useTransform } from "motion/react";
import { useRef } from "react";

/**
 * 3D tilt-toward-cursor for cards. Uses `transform-style: preserve-3d` and rotates the
 * surface on rX/rY based on cursor offset from card center. A subtle glare highlight tracks
 * the cursor in screen space.
 */
export function Tilt({
  children,
  className = "",
  max = 8,
  glare = true,
}: {
  children: React.ReactNode;
  className?: string;
  max?: number;
  glare?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const px = useMotionValue(0.5);
  const py = useMotionValue(0.5);

  const rotateX = useSpring(useTransform(py, [0, 1], [max, -max]), {
    stiffness: 200,
    damping: 22,
  });
  const rotateY = useSpring(useTransform(px, [0, 1], [-max, max]), {
    stiffness: 200,
    damping: 22,
  });

  const glareX = useTransform(px, (v) => `${v * 100}%`);
  const glareY = useTransform(py, (v) => `${v * 100}%`);

  const onMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    px.set((e.clientX - r.left) / r.width);
    py.set((e.clientY - r.top) / r.height);
  };

  const onLeave = () => {
    px.set(0.5);
    py.set(0.5);
  };

  return (
    <motion.div
      ref={ref}
      onPointerMove={onMove}
      onPointerLeave={onLeave}
      style={{
        rotateX,
        rotateY,
        transformStyle: "preserve-3d",
        transformPerspective: 900,
      }}
      className={`relative ${className}`}
    >
      {children}
      {glare && (
        <motion.div
          aria-hidden
          style={{
            background: `radial-gradient(220px circle at ${glareX.get()} ${glareY.get()}, rgba(255,255,255,0.10), transparent 60%)`,
          }}
          className="absolute inset-0 pointer-events-none mix-blend-overlay"
        />
      )}
    </motion.div>
  );
}
