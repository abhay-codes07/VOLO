import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  typedRoutes: true,
  // Emit a self-contained server bundle (.next/standalone) for a slim runtime
  // image. No effect on `next dev` / `next start`; see apps/web/Dockerfile.
  output: "standalone",
};

export default config;
