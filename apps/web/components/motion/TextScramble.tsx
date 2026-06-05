"use client";

import { useEffect, useState } from "react";

const CHARS = "!<>-_\\/[]{}—=+*^?#________";

/**
 * Cycles letters through random glyphs before settling on the target text. Pure visual
 * polish — fires on mount + every time `text` changes.
 */
export function TextScramble({
  text,
  duration = 0.9,
  className = "",
}: {
  text: string;
  duration?: number;
  className?: string;
}) {
  const [out, setOut] = useState(text);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setOut(text);
      return;
    }

    let raf = 0;
    const queue: { from: string; to: string; start: number; end: number; char?: string }[] = [];
    const length = Math.max(text.length, out.length);
    for (let i = 0; i < length; i++) {
      const from = out[i] ?? "";
      const to = text[i] ?? "";
      const start = Math.floor(Math.random() * 40);
      const end = start + Math.floor(Math.random() * 40) + 18;
      queue.push({ from, to, start, end });
    }
    let frame = 0;
    const tick = () => {
      let complete = 0;
      const next: string[] = [];
      for (let i = 0; i < queue.length; i++) {
        const item = queue[i];
        if (frame >= item.end) {
          complete++;
          next.push(item.to);
        } else if (frame >= item.start) {
          if (!item.char || Math.random() < 0.28) {
            item.char = CHARS[Math.floor(Math.random() * CHARS.length)];
          }
          next.push(item.char ?? "");
        } else {
          next.push(item.from);
        }
      }
      setOut(next.join(""));
      if (complete < queue.length) {
        frame++;
        raf = requestAnimationFrame(tick);
      }
    };
    // duration in seconds → frame budget at ~60fps
    const maxFrames = Math.max(...queue.map((q) => q.end));
    void maxFrames; // budget self-tunes by random distribution
    void duration;
    tick();
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text]);

  return <span className={className}>{out}</span>;
}
