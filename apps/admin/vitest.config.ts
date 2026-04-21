import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    environment: "node",
    // Playwright specs live alongside vitest tests but are run by Playwright,
    // not vitest. Without excluding them, vitest tries to import them and
    // crashes on the @playwright/test runner globals.
    exclude: ["e2e/**", "node_modules/**", ".next/**"],
    // Jest-DOM matchers (toBeInTheDocument etc.) wired for all test files.
    // Component tests opt into jsdom via the file-level comment:
    //   // @vitest-environment jsdom
    // Node-based tests (route handlers) continue to run in node.
    setupFiles: ["./vitest.setup.ts"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
});
