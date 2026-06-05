"use client";

import { motion } from "motion/react";
import Link from "next/link";
import { useState } from "react";
import { AuroraBackdrop } from "@/components/motion/AuroraBackdrop";
import { Magnetic } from "@/components/motion/Magnetic";
import { TextScramble } from "@/components/motion/TextScramble";

export default function LoginPage() {
  const [signingIn, setSigningIn] = useState(false);

  return (
    <main className="relative min-h-screen overflow-hidden flex flex-col">
      {/* aurora */}
      <div className="absolute inset-0 -z-10">
        <AuroraBackdrop />
      </div>

      {/* top bar */}
      <header className="relative z-10 max-w-7xl mx-auto w-full px-6 md:px-10 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5 group">
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 280, damping: 16 }}
            className="inline-block w-2.5 h-2.5 rounded-full bg-signal-nominal shadow-glow-nominal"
          />
          <span className="font-display text-lg font-semibold tracking-tighter text-text-hi">
            Volo
          </span>
        </Link>
        <Link
          href="/"
          className="font-mono text-[11px] uppercase tracking-widest text-text-lo hover:text-text-hi transition-colors"
        >
          ← back
        </Link>
      </header>

      {/* center card */}
      <div className="relative flex-1 flex items-center justify-center px-6">
        <motion.div
          initial={{ opacity: 0, y: 24, filter: "blur(8px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.85, ease: [0.16, 1, 0.3, 1] }}
          className="relative w-full max-w-md"
        >
          {/* glow halo */}
          <div
            aria-hidden
            className="absolute -inset-8 rounded-3xl pointer-events-none"
            style={{
              background:
                "radial-gradient(60% 60% at 50% 0%, rgba(61,224,184,0.18), transparent 70%)",
              filter: "blur(28px)",
            }}
          />

          <div className="relative hairline bg-surface-1/80 backdrop-blur-xl shadow-elev-2 rounded-md overflow-hidden">
            {/* top brand strip */}
            <div className="px-7 pt-7 pb-5 border-b border-border-1">
              <div className="flex items-center gap-2 mb-5">
                <span className="dot-live" />
                <span className="font-mono text-[10px] uppercase tracking-widest text-text-mute">
                  control room
                </span>
              </div>
              <h1 className="font-display text-3xl font-semibold tracking-tighter text-text-hi mb-1.5">
                <TextScramble text="Welcome back" />
              </h1>
              <p className="font-mono text-[12px] text-text-lo">
                Continue to your Volo dashboard.
              </p>
            </div>

            {/* body */}
            <div className="px-7 py-7 space-y-3">
              <Magnetic strength={0.25}>
                <button
                  onClick={() => {
                    setSigningIn(true);
                    setTimeout(() => (window.location.href = "/"), 900);
                  }}
                  data-cursor="hover"
                  className="w-full btn-primary justify-center !py-3 !text-[13px]"
                >
                  {signingIn ? (
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex items-center gap-2"
                    >
                      <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="32" strokeLinecap="round" />
                      </svg>
                      ENTERING
                    </motion.span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <GitHubIcon /> CONTINUE WITH GITHUB
                    </span>
                  )}
                </button>
              </Magnetic>

              <Magnetic strength={0.25}>
                <Link
                  href="/"
                  data-cursor="hover"
                  className="w-full btn-secondary justify-center !py-3 !text-[13px]"
                >
                  CONTINUE AS GUEST
                </Link>
              </Magnetic>

              <div className="flex items-center gap-3 py-2 text-text-mute font-mono text-[10px] uppercase tracking-widest">
                <span className="flex-1 h-px bg-border-1" />
                <span>or use</span>
                <span className="flex-1 h-px bg-border-1" />
              </div>

              <div className="grid grid-cols-2 gap-2">
                {[
                  { label: "Google",  icon: <GoogleIcon /> },
                  { label: "Email",   icon: <EmailIcon /> },
                ].map((p) => (
                  <motion.button
                    key={p.label}
                    whileHover={{ y: -2 }}
                    whileTap={{ scale: 0.97 }}
                    transition={{ type: "spring", stiffness: 320, damping: 22 }}
                    data-cursor="hover"
                    className="hairline bg-surface-2/40 px-3 py-2.5 font-mono text-[11px] uppercase tracking-widest text-text-lo hover:text-text-hi hover:border-border-2 transition-colors flex items-center justify-center gap-2"
                  >
                    {p.icon}
                    {p.label}
                  </motion.button>
                ))}
              </div>
            </div>

            {/* footer */}
            <div className="px-7 py-4 border-t border-border-1 bg-surface-2/30 flex items-center justify-between font-mono text-[10px] uppercase tracking-widest text-text-mute">
              <span>Apache-2.0</span>
              <span>v0.1.0 · pre-alpha</span>
            </div>
          </div>

          <p className="mt-6 text-center font-mono text-[10px] uppercase tracking-widest text-text-mute">
            By continuing, you agree to the terms · privacy
          </p>
        </motion.div>
      </div>

      {/* corner status */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.2, duration: 0.8 }}
        className="relative z-10 max-w-7xl mx-auto w-full px-6 md:px-10 pb-6 flex items-center justify-between font-mono text-[10px] uppercase tracking-widest text-text-mute"
      >
        <span>flight-test control room</span>
        <span className="flex items-center gap-2">
          <span className="dot-live" /> systems nominal
        </span>
      </motion.div>
    </main>
  );
}

function GitHubIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-3.5 h-3.5" fill="currentColor">
      <path d="M12 .3a12 12 0 0 0-3.8 23.4c.6.1.8-.3.8-.6v-2.1c-3.3.7-4-1.6-4-1.6-.5-1.3-1.3-1.7-1.3-1.7-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1.1 1.8 2.8 1.3 3.4 1 .1-.8.4-1.3.8-1.6-2.7-.3-5.5-1.3-5.5-6 0-1.3.5-2.4 1.2-3.2-.1-.3-.5-1.5.1-3.2 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0c2.3-1.5 3.3-1.2 3.3-1.2.7 1.7.3 2.9.1 3.2.8.8 1.2 1.9 1.2 3.2 0 4.7-2.8 5.7-5.5 6 .4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A12 12 0 0 0 12 .3"/>
    </svg>
  );
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-3.5 h-3.5" fill="none">
      <path d="M22 12a10 10 0 1 1-3-7.1l-2.9 2.9A6 6 0 1 0 18 12h-6V8h10v4z" fill="currentColor"/>
    </svg>
  );
}

function EmailIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="5" width="18" height="14" rx="1.5"/>
      <path d="M3 7l9 6 9-6"/>
    </svg>
  );
}
