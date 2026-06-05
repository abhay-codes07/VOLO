"use client";

import { motion, type Variants } from "motion/react";

/**
 * Section-level reveal — fade + lift on first scroll into view.
 */
export function Reveal({
  children,
  delay = 0,
  y = 24,
  className = "",
}: {
  children: React.ReactNode;
  delay?: number;
  y?: number;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1], delay }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

const STAGGER_PARENT: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06, delayChildren: 0.05 } },
};

const STAGGER_CHILD: Variants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] } },
};

export function Stagger({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <motion.div
      variants={STAGGER_PARENT}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "-60px" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <motion.div variants={STAGGER_CHILD} className={className}>
      {children}
    </motion.div>
  );
}
