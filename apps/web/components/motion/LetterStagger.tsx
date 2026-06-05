"use client";

import { motion, type Variants } from "motion/react";

/**
 * Word-by-word stagger reveal on the hero headline.
 */
const PARENT: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.05, delayChildren: 0.15 } },
};

const CHILD: Variants = {
  hidden: { opacity: 0, y: "120%", rotateX: -45 },
  show: {
    opacity: 1,
    y: 0,
    rotateX: 0,
    transition: { duration: 0.85, ease: [0.16, 1, 0.3, 1] },
  },
};

export function LetterStagger({
  children,
  className = "",
  as = "span",
}: {
  children: string;
  className?: string;
  as?: keyof Pick<JSX.IntrinsicElements, "h1" | "h2" | "span" | "div">;
}) {
  const words = children.split(" ");
  const Tag = motion[as as "span"];
  return (
    <Tag
      variants={PARENT}
      initial="hidden"
      animate="show"
      className={className}
      style={{ perspective: 900 }}
    >
      {words.map((w, i) => (
        <span key={i} className="inline-block overflow-hidden align-baseline">
          <motion.span variants={CHILD} className="inline-block will-change-transform">
            {w}
            {i < words.length - 1 && " "}
          </motion.span>
        </span>
      ))}
    </Tag>
  );
}
