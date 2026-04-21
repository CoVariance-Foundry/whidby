import { defineConfig, devices } from "@playwright/test";
import path from "path";

const appDir = path.resolve(__dirname);

export default defineConfig({
  testDir: path.join(appDir, "e2e"),
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL: "http://localhost:3001",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: `npm run dev --workspace=nichefinder-app`,
    url: "http://localhost:3001/login",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
