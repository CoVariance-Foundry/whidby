import { Page, expect } from "@playwright/test";

/**
 * Shared Playwright helpers for the consumer app's auth-dependent tests.
 *
 * The test account is documented in the repo-level CLAUDE.md under
 * "Auth & Test Accounts". Prefer the `E2E_AUTH_EMAIL` / `E2E_AUTH_PASSWORD`
 * env vars — fall back to the documented `e2e-test@widby.dev` credential only
 * for convenience on local dev machines.
 */

const DEFAULT_EMAIL = "e2e-test@widby.dev";
const DEFAULT_PASSWORD = "WidbyTest2026!";

export type SignInOptions = {
  email?: string;
  password?: string;
  /** URL (or pattern) we expect to land on after submit. Defaults to "anything non-/login". */
  expectLandOn?: string | RegExp | ((url: URL) => boolean);
  /** Timeout for post-submit URL assertion. */
  timeoutMs?: number;
  /** Optional query string (including leading "?next=...") to include when
   *  first visiting /login. Used by next= round-trip tests. */
  loginQuery?: string;
};

/**
 * Perform a UI sign-in on /login and wait until we've left the login route.
 *
 * Note: the login form does not use <label for=...> so role/placeholder
 * selectors are used instead of getByLabel.
 */
export async function signIn(
  page: Page,
  opts: SignInOptions = {},
): Promise<void> {
  const email = opts.email ?? process.env.E2E_AUTH_EMAIL ?? DEFAULT_EMAIL;
  const password =
    opts.password ?? process.env.E2E_AUTH_PASSWORD ?? DEFAULT_PASSWORD;
  const timeout = opts.timeoutMs ?? 15_000;

  const loginPath = opts.loginQuery
    ? `/login${opts.loginQuery.startsWith("?") ? "" : "?"}${opts.loginQuery}`
    : "/login";
  await page.goto(loginPath);

  await page.getByPlaceholder("you@example.com").fill(email);
  await page.getByPlaceholder("••••••••").fill(password);
  await page.getByRole("button", { name: /sign in/i }).click();

  if (opts.expectLandOn !== undefined) {
    await page.waitForURL(opts.expectLandOn, { timeout });
  } else {
    await page.waitForURL((url) => !url.pathname.startsWith("/login"), {
      timeout,
    });
  }
}

/**
 * Returns true iff the authenticated-layout marker (the Widby sidebar brand
 * mark) is visible — used as a quick check after a redirect.
 */
export async function isSignedIn(page: Page): Promise<boolean> {
  try {
    await expect(page.locator(".sidebar-brand-mark").first()).toBeVisible({
      timeout: 3_000,
    });
    return true;
  } catch {
    return false;
  }
}

/** Whether the current environment provides non-default auth credentials. */
export const hasE2ECredentials = (): boolean =>
  typeof process.env.E2E_AUTH_EMAIL === "string" &&
  process.env.E2E_AUTH_EMAIL.length > 0;
