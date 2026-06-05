"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/cn";

/**
 * shadcn-style Button primitive, restyled with Volo instrument-panel tokens
 * (bible §8.4 — don't ship default shadcn).
 *
 * Variants map to the same CSS classes the rest of the app already uses
 * (`.btn-primary`, `.btn-secondary`) plus a new `ghost` variant for top-bar density.
 */
const button = cva(
  "inline-flex items-center justify-center gap-2 font-mono text-[13px] tracking-[0.02em] font-medium transition-all focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal-info disabled:opacity-50 disabled:pointer-events-none",
  {
    variants: {
      variant: {
        primary:
          "bg-signal-nominal text-surface-0 border border-signal-nominal hover:shadow-glow-nominal hover:-translate-y-px font-semibold",
        secondary:
          "bg-transparent text-text-hi border border-border-2 hover:border-border-3",
        ghost:
          "bg-transparent text-text-lo hover:bg-surface-2 hover:text-text-hi border border-transparent",
        danger:
          "bg-signal-failure/15 text-signal-failure border border-signal-failure/40 hover:bg-signal-failure/25",
      },
      size: {
        sm: "px-3 py-1.5 text-[11px]",
        md: "px-4 py-2 text-[12px]",
        lg: "px-5 py-2.5 text-[13px]",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof button> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp ref={ref} className={cn(button({ variant, size }), className)} {...props} />;
  },
);
Button.displayName = "Button";

export { button as buttonVariants };
