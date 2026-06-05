"use client";

import { motion } from "motion/react";
import { MagneticButton } from "@/components/motion/MagneticButton";

export function CTA() {
  return (
    <section className="relative max-w-7xl mx-auto px-6 md:px-10 py-28">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-60px" }}
        transition={{ duration: 0.85, ease: [0.16, 1, 0.3, 1] }}
        className="relative hairline-2 bg-surface-1 overflow-hidden"
      >
        <div
          aria-hidden
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              "radial-gradient(50% 80% at 50% 0%, rgba(61,224,184,0.22), transparent 70%), radial-gradient(40% 60% at 10% 100%, rgba(111,170,255,0.10), transparent 70%), radial-gradient(40% 60% at 90% 100%, rgba(182,121,255,0.10), transparent 70%)",
          }}
        />
        <div className="relative p-12 md:p-24 text-center">
          <h2 className="font-serif text-[clamp(2.5rem,8vw,7rem)] leading-[0.98] tracking-tight text-text-hi mb-10">
            Ship the <em className="text-signal-nominal">agent</em>.
          </h2>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <MagneticButton href="/auth/login" variant="primary">Open dashboard ↘</MagneticButton>
            <MagneticButton href="https://github.com/volo-sim/volo" variant="secondary" external>★ GitHub</MagneticButton>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
