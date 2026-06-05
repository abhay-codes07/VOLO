import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3001",
    trace: "on-first-retry",
  },
  webServer: process.env.CI
    ? {
        command: "npm run dev",
        url: "http://localhost:3001",
        reuseExistingServer: false,
        timeout: 60_000,
      }
    : undefined,
});
