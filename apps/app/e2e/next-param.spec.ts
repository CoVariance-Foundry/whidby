import { test, expect } from "@playwright/test";
import { signIn, hasE2ECredentials } from "./helpers/auth";

/**
 * Exhaustive coverage of the `next=` round-trip and open-redirect rejection
 * against the consumer app's auth gate. `isSafeNext` (src/lib/auth/safe-next.ts)
 * is validated at three entry points — the proxy, the /login form, and the
 * /auth/callback route — so every assertion here is effectively end-to-end.
 *
 * Auth-dependent tests skip when E2E_AUTH_EMAIL is not set so local runs
 * without credentials don't fail. Set E2E_AUTH_EMAIL + E2E_AUTH_PASSWORD
 * against a real Supabase account (the documented `e2e-test@widby.dev`
 * account must exist on the project) to run the authenticated flows.
 */

test.describe("next= round-trip — unauthenticated flow", () => {
  test("unauth /reports -> /login?next=/reports", async ({ page }) => {
    await page.goto("/reports");
    await page.waitForURL(/\/login\?next=%2Freports$/, { timeout: 10_000 });
    const url = new URL(page.url());
    expect(url.pathname).toBe("/login");
    expect(url.searchParams.get("next")).toBe("/reports");
  });

  test("unauth /reports/:id -> /login?next=/reports/:id (deep path)", async ({
    page,
  }) => {
    await page.goto("/reports/any-id-123");
    await page.waitForURL(/\/login\?next=/, { timeout: 10_000 });
    const url = new URL(page.url());
    expect(url.pathname).toBe("/login");
    expect(url.searchParams.get("next")).toBe("/reports/any-id-123");
  });

  test("unauth /login itself does not append ?next= (no self-loop)", async ({
    page,
  }) => {
    await page.goto("/login");
    // Assert /login rendered and the query string has no next= key.
    await expect(page.getByPlaceholder("you@example.com")).toBeVisible();
    const url = new URL(page.url());
    expect(url.pathname).toBe("/login");
    expect(url.searchParams.get("next")).toBeNull();
  });

  test("/auth/callback is public — not redirected by the gate", async ({
    page,
  }) => {
    // Hit /auth/callback with no `code` param. The route handler itself will
    // redirect to /login with an explicit error=, but crucially the proxy
    // must let the request pass through to that handler in the first place
    // instead of bouncing to /login?next=/auth/callback.
    const response = await page.goto("/auth/callback");
    // The handler responds with a 307/302 redirect to /login?error=...; what
    // matters is the landing URL carries the explicit error code, not a next=.
    expect(response?.ok() || response?.status() === 307 || response?.status() === 302).toBeTruthy();
    const url = new URL(page.url());
    // Either we land on /login?error=... (the handler's redirect) or we stay
    // on /auth/callback; both prove the gate passed it through.
    if (url.pathname === "/login") {
      expect(url.searchParams.get("error")).toBe("auth_callback_failed");
      // Must NOT have a `next` param pointing back at /auth/callback.
      expect(url.searchParams.get("next")).toBeNull();
    } else {
      expect(url.pathname).toBe("/auth/callback");
    }
  });
});

test.describe("next= round-trip — authenticated flow", () => {
  test.skip(
    !hasE2ECredentials(),
    "requires E2E_AUTH_EMAIL / E2E_AUTH_PASSWORD (see CLAUDE.md Auth & Test Accounts)",
  );

  test("sign in without next -> lands on /reports", async ({ page }) => {
    await signIn(page, { expectLandOn: /\/reports(\?|$)/ });
    expect(new URL(page.url()).pathname).toBe("/reports");
  });

  test("sign in with ?next=/reports -> lands on /reports", async ({ page }) => {
    await signIn(page, {
      loginQuery: "?next=%2Freports",
      expectLandOn: /\/reports(\?|$)/,
    });
    expect(new URL(page.url()).pathname).toBe("/reports");
  });

  test("sign in with deep ?next=/reports/R-0148 -> lands on that path", async ({
    page,
  }) => {
    await signIn(page, {
      loginQuery: "?next=%2Freports%2FR-0148",
      // /reports/R-0148 will 404 against the current route tree; we only
      // validate URL behavior, not page content.
      expectLandOn: /\/reports\/R-0148$/,
    });
    expect(new URL(page.url()).pathname).toBe("/reports/R-0148");
  });

  test("sign in with ?next=/reports?filter=abc preserves query", async ({
    page,
  }) => {
    await signIn(page, {
      loginQuery: "?next=%2Freports%3Ffilter%3Dabc",
      expectLandOn: /\/reports\?filter=abc$/,
    });
    const url = new URL(page.url());
    expect(url.pathname).toBe("/reports");
    expect(url.searchParams.get("filter")).toBe("abc");
  });
});

test.describe("next= round-trip — open-redirect rejection", () => {
  test.skip(
    !hasE2ECredentials(),
    "requires E2E_AUTH_EMAIL / E2E_AUTH_PASSWORD (see CLAUDE.md Auth & Test Accounts)",
  );

  test("?next=//evil.com is ignored -> lands on /reports", async ({ page }) => {
    await signIn(page, {
      loginQuery: "?next=%2F%2Fevil.com",
      expectLandOn: /\/reports(\?|$)/,
    });
    const url = new URL(page.url());
    expect(url.hostname).toBe("localhost");
    expect(url.pathname).toBe("/reports");
  });

  test("?next=/\\evil.com is ignored -> lands on /reports", async ({ page }) => {
    // %2F = "/", %5C = "\"
    await signIn(page, {
      loginQuery: "?next=%2F%5Cevil.com",
      expectLandOn: /\/reports(\?|$)/,
    });
    const url = new URL(page.url());
    expect(url.hostname).toBe("localhost");
    expect(url.pathname).toBe("/reports");
  });

  test("?next=https://evil.com is ignored -> lands on /reports", async ({
    page,
  }) => {
    await signIn(page, {
      loginQuery: "?next=https%3A%2F%2Fevil.com",
      expectLandOn: /\/reports(\?|$)/,
    });
    const url = new URL(page.url());
    expect(url.hostname).toBe("localhost");
    expect(url.pathname).toBe("/reports");
  });
});

test.describe("next= round-trip — authed user visits /login", () => {
  test.skip(
    !hasE2ECredentials(),
    "requires E2E_AUTH_EMAIL / E2E_AUTH_PASSWORD (see CLAUDE.md Auth & Test Accounts)",
  );

  // These tests share a browser context so the Supabase session cookie set
  // by the first sign-in is available for subsequent /login visits.
  test.describe.configure({ mode: "serial" });

  test("already-authed visit to /login -> /reports", async ({ page }) => {
    await signIn(page, { expectLandOn: /\/reports(\?|$)/ });
    // Now already authenticated — hit /login again.
    await page.goto("/login");
    await page.waitForURL(/\/reports(\?|$)/, { timeout: 10_000 });
    expect(new URL(page.url()).pathname).toBe("/reports");
  });

  test("already-authed visit to /login?next=/reports/specific honors next", async ({
    page,
  }) => {
    await signIn(page, { expectLandOn: /\/reports(\?|$)/ });
    await page.goto("/login?next=%2Freports%2Fspecific");
    await page.waitForURL(/\/reports\/specific$/, { timeout: 10_000 });
    expect(new URL(page.url()).pathname).toBe("/reports/specific");
  });
});
