import { defineConfig, devices } from "@playwright/test";
import path from "path";

const appDir = path.resolve(__dirname);
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3002";

export default defineConfig({
  testDir: path.join(appDir, "e2e"),
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
      testIgnore: ["**/scoring-matrix*"],
    },
    {
      name: "scoring-matrix",
      use: { ...devices["Desktop Chrome"] },
      testMatch: "**/scoring-matrix*",
      timeout: 180_000,
    },
  ],
  webServer: process.env.PLAYWRIGHT_BASE_URL
    ? undefined
    : {
        command: `npm run dev --workspace=widby-app`,
        url: "http://localhost:3002/login",
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
});
