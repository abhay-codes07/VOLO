"use client";

import { Magnetic } from "./Magnetic";

export function MagneticButton({
  children,
  href,
  variant = "primary",
  external = false,
}: {
  children: React.ReactNode;
  href: string;
  variant?: "primary" | "secondary";
  external?: boolean;
}) {
  const cls = variant === "primary" ? "btn-primary" : "btn-secondary";
  const linkProps = external
    ? { target: "_blank" as const, rel: "noreferrer" as const }
    : {};
  return (
    <Magnetic>
      <a href={href} {...linkProps} className={cls}>
        {children}
      </a>
    </Magnetic>
  );
}
