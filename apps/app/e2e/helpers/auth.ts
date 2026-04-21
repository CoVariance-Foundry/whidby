import { type Page } from "@playwright/test";

/**
 * Log in via the password form using env-provided credentials.
 * Falls back to E2E_AUTH_EMAIL / E2E_AUTH_PASSWORD env vars so
 * Vercel preview and CI can run authenticated tests without secrets
 * in code.
 */
export async function loginWithPassword(
  page: Page,
  email?: string,
  password?: string,
) {
  const e = email ?? process.env.E2E_AUTH_EMAIL;
  const p = password ?? process.env.E2E_AUTH_PASSWORD;

  if (!e || !p) {
    throw new Error(
      "E2E login credentials missing. Set E2E_AUTH_EMAIL and E2E_AUTH_PASSWORD.",
    );
  }

  await page.goto("/login");
  await page.getByLabel("Email address").fill(e);
  await page.getByLabel("Password").fill(p);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("**/", { timeout: 15_000 });
}
