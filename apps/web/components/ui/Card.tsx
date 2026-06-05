"use client";

import * as React from "react";
import { cn } from "@/lib/cn";

/** Volo-styled card primitive — the same `.hairline.bg-surface-1` look used everywhere. */
export const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("hairline bg-surface-1 shadow-elev-1", className)}
      {...props}
    />
  ),
);
Card.displayName = "Card";

export const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("px-5 py-3 border-b border-border-1 bg-surface-2/40 flex items-center justify-between", className)}
      {...props}
    />
  ),
);
CardHeader.displayName = "CardHeader";

export const CardTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3
      ref={ref}
      className={cn("font-mono text-[11px] uppercase tracking-widest text-text-mute", className)}
      {...props}
    />
  ),
);
CardTitle.displayName = "CardTitle";

export const CardBody = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("p-5", className)} {...props} />
  ),
);
CardBody.displayName = "CardBody";

export const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("px-5 py-3 border-t border-border-1 bg-surface-2/40 font-mono text-[11px] text-text-mute flex items-center justify-between", className)}
      {...props}
    />
  ),
);
CardFooter.displayName = "CardFooter";
