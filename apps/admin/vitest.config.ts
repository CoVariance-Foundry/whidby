import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    environment: "node",
    // Playwright specs live alongside vitest tests but are run by Playwright,
    // not vitest. Without excluding them, vitest tries to import them and
    // crashes on the @playwright/test runner globals.
    exclude: ["e2e/**", "node_modules/**", ".next/**"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
});
