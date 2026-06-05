"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "motion/react";

const NAV_ITEMS = [
  { href: "/",          label: "Overview" },
  { href: "/runs",      label: "Runs" },
  { href: "/ci",        label: "CI" },
  { href: "/scenarios", label: "Scenarios" },
  { href: "/diff",      label: "Diff" },
] as const;

export function TopNav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-30 border-b border-border-1 glass">
      <div className="max-w-7xl mx-auto px-6 md:px-10 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5 group" data-cursor="hover">
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

        <nav className="hidden md:flex items-center gap-0.5">
          {NAV_ITEMS.map((it) => {
            const active = pathname === it.href || (it.href !== "/" && pathname.startsWith(it.href));
            return (
              <Link
                key={it.href}
                href={it.href as never}
                data-cursor="hover"
                className="relative px-3 py-1.5 font-mono text-[12px] uppercase tracking-widest text-text-lo hover:text-text-hi transition-colors"
              >
                {active && (
                  <motion.span
                    layoutId="nav-pill"
                    className="absolute inset-0 bg-surface-2 hairline rounded-md -z-0"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
                <span className={`relative z-10 ${active ? "text-signal-nominal" : ""}`}>
                  {it.label}
                </span>
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-3">
          <Link
            href="/auth/login"
            data-cursor="hover"
            className="btn-primary !py-1.5 !px-3.5 text-[12px]"
          >
            Open dashboard
          </Link>
        </div>
      </div>
    </header>
  );
}
