"use client";

import { motion, useMotionValue, useSpring } from "motion/react";
import { useEffect, useState } from "react";

/**
 * A two-layer cursor: a 6px solid dot that snaps to the mouse, and a 28px ring that lags
 * behind with spring physics. The ring grows + softens when hovering anchors / buttons.
 * Hidden on touch. Respects prefers-reduced-motion.
 */
export function CursorHalo() {
  const dotX = useMotionValue(-100);
  const dotY = useMotionValue(-100);
  const ringX = useSpring(dotX, { stiffness: 180, damping: 22, mass: 0.6 });
  const ringY = useSpring(dotY, { stiffness: 180, damping: 22, mass: 0.6 });

  const [hover, setHover] = useState(false);
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (window.matchMedia("(pointer: coarse)").matches) return;
    setEnabled(true);

    const move = (e: PointerEvent) => {
      dotX.set(e.clientX);
      dotY.set(e.clientY);
    };
    const over = (e: PointerEvent) => {
      const t = e.target as HTMLElement;
      const interactive = t.closest("a, button, [data-cursor='hover'], input, textarea, [role='button']");
      setHover(!!interactive);
    };

    window.addEventListener("pointermove", move, { passive: true });
    window.addEventListener("pointerover", over, { passive: true });
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerover", over);
    };
  }, [dotX, dotY]);

  if (!enabled) return null;

  return (
    <>
      <motion.div
        aria-hidden
        style={{ x: dotX, y: dotY }}
        className="pointer-events-none fixed left-0 top-0 z-[100] mix-blend-screen"
      >
        <div className="-translate-x-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-signal-nominal shadow-[0_0_12px_var(--signal-nominal)]" />
      </motion.div>
      <motion.div
        aria-hidden
        style={{ x: ringX, y: ringY }}
        className="pointer-events-none fixed left-0 top-0 z-[99] mix-blend-screen"
      >
        <motion.div
          animate={{
            width:  hover ? 56 : 28,
            height: hover ? 56 : 28,
            opacity: hover ? 0.9 : 0.55,
            borderColor: hover ? "rgba(61,224,184,0.95)" : "rgba(180,200,230,0.55)",
          }}
          transition={{ type: "spring", stiffness: 240, damping: 22 }}
          className="-translate-x-1/2 -translate-y-1/2 rounded-full border"
          style={{ boxShadow: hover ? "0 0 32px rgba(61,224,184,0.4)" : "none" }}
        />
      </motion.div>
    </>
  );
}
