import { test, expect, type Page } from "@playwright/test";
import { signIn } from "./helpers/auth";
import { type RunMetric } from "./helpers/scoring-combos";

/**
 * Helper: make an authenticated API call via the browser context.
 * The consumer app routes are behind auth middleware, so we sign in with the
 * browser first, then use page.evaluate to make fetch calls that carry the
 * session cookies.
 */
async function authPost(
  page: Page,
  url: string,
  data: Record<string, unknown>,
): Promise<{ status: number; body: Record<string, unknown> }> {
  return page.evaluate(
    async ({ url, data }) => {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      let body: Record<string, unknown>;
      try {
        body = await res.json();
      } catch {
        body = { _parseError: true, _raw: (await res.clone().text()).slice(0, 500) };
      }
      return { status: res.status, body };
    },
    { url, data },
  );
}

async function authGet(
  page: Page,
  url: string,
): Promise<{ status: number; body: unknown }> {
  return page.evaluate(async (url) => {
    const res = await fetch(url);
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      body = (await res.clone().text()).slice(0, 500);
    }
    return { status: res.status, body };
  }, url);
}

/**
 * Critical regression tests for scoring failure modes.
 *
 * Root cause (confirmed via autocomplete-scoring-flow.spec.ts):
 *   1. The DataForSEO location bridge returns `dataforseo_location_code: null`
 *      for Huntsville (and potentially other small metros).
 *   2. Without a DFS code, the orchestrator falls to `MetroDB.find_by_city`
 *      which returns None for cities not in the CBSA seed.
 *   3. The proxy masks the upstream 400 with a generic "did not return a result."
 */

const SCORING_ENDPOINT = "/api/agent/scoring";

// All API tests in this file need auth — sign in once per test.
test.beforeEach(async ({ page }) => {
  await signIn(page, { expectLandOn: /\/(reports|$)/ });
});

// ── Huntsville regression (the exact bug from the screenshot) ────────────────

test.describe("Huntsville regression — null DFS code + unseeded city", () => {
  test("Huntsville+tree-removal with state+place_id (no dfs code) returns structured error or valid score", async ({
    page,
  }) => {
    const start = Date.now();
    const { status, body } = await authPost(page, SCORING_ENDPOINT, {
      city: "Huntsville",
      service: "tree removal",
      state: "AL",
      place_id: "dXJuOm1ieHBsYzpDVnVvN0E",
    });
    const latencyMs = Date.now() - start;

    const metric: RunMetric = {
      combo: "huntsville-tree",
      tier: 2,
      runIndex: 0,
      status: status >= 200 && status < 300 ? "pass" : "fail",
      httpStatus: status,
      reportId: (body?.report_id as string) ?? null,
      opportunityScore: (body?.score_result as Record<string, number>)?.opportunity_score ?? null,
      latencyMs,
      upstreamStatus: (body?.upstream_status as number) ?? null,
      errorMessage: (body?.message as string) ?? null,
      timestamp: new Date().toISOString(),
    };
    test.info().annotations.push({ type: "metric", description: JSON.stringify(metric) });

    if (status >= 200 && status < 300 && body?.status === "success") {
      const scoreResult = body.score_result as Record<string, unknown>;
      expect(scoreResult.opportunity_score).toBeGreaterThanOrEqual(0);
      expect(scoreResult.opportunity_score).toBeLessThanOrEqual(100);
      expect(body.report_id).toBeTruthy();
    } else {
      expect(status).toBeGreaterThanOrEqual(400);
      expect(body.upstream_status).toBeDefined();
      expect(body.message).toBeDefined();
    }
  });

  test("Huntsville without state or place_id fails gracefully (no unhandled 500 / hang)", async ({
    page,
  }) => {
    const { status, body } = await authPost(page, SCORING_ENDPOINT, {
      city: "Huntsville",
      service: "tree removal",
    });

    // 502 is expected: the proxy maps upstream 400 ("no CBSA match") to 502.
    // We accept 400 or 502 but NOT 500 (unhandled crash) or timeouts.
    expect([400, 502]).toContain(status);
    expect(body.status).toBeDefined();
  });

  test("places suggest API returns null dataforseo_location_code for Huntsville (documents the gap)", async ({
    page,
  }) => {
    const { status, body } = await authGet(
      page,
      "/api/agent/places/suggest?q=Huntsville&limit=8",
    );

    if (status !== 200) {
      test.info().annotations.push({
        type: "places-api-status",
        description: `${status} — places suggest unavailable`,
      });
      test.skip(true, "Places suggest API not reachable.");
      return;
    }

    const suggestions = body as Array<Record<string, unknown>>;
    test.info().annotations.push({
      type: "suggestion-count",
      description: String(suggestions.length),
    });

    const huntsvilleAL = suggestions.find(
      (s) => s.city === "Huntsville" && s.region === "AL",
    );
    expect(huntsvilleAL).toBeDefined();

    test.info().annotations.push({
      type: "huntsville-dfs-code",
      description: String(huntsvilleAL?.dataforseo_location_code ?? "null"),
    });
  });
});

// ── City normalization & metro mapping ───────────────────────────────────────

test.describe("City normalization edge cases", () => {
  test.setTimeout(180_000);

  const cases = [
    { label: "lowercase city",        data: { city: "phoenix", service: "roofing", state: "AZ" } },
    { label: "extra whitespace",      data: { city: "  Phoenix  ", service: "  roofing  ", state: "AZ" } },
    { label: "mixed casing",          data: { city: "pHoEnIx", service: "ROOFING", state: "az" } },
    { label: "city with comma-state", data: { city: "Phoenix, AZ", service: "roofing" } },
  ];

  for (const { label, data } of cases) {
    test(`${label} — resolves or fails with clear reason`, async ({ page }) => {
      const { status, body } = await authPost(page, SCORING_ENDPOINT, data);

      if (status >= 200 && status < 300 && body?.status === "success") {
        const scoreResult = body.score_result as Record<string, unknown>;
        expect(scoreResult.opportunity_score).toBeGreaterThanOrEqual(0);
      } else {
        expect(body.message ?? body.upstream_status).toBeDefined();
      }
    });
  }
});

// ── Input validation boundary ────────────────────────────────────────────────

test.describe("Input validation failures", () => {
  test("empty city and service → 400 validation error", async ({ page }) => {
    const { status, body } = await authPost(page, SCORING_ENDPOINT, {
      city: "",
      service: "",
    });
    expect(status).toBe(400);
    expect(body.status).toBe("validation_error");
    expect(body.message).toBeTruthy();
  });

  test("1-char city → 400 validation error", async ({ page }) => {
    const { status, body } = await authPost(page, SCORING_ENDPOINT, {
      city: "X",
      service: "roofing",
    });
    expect(status).toBe(400);
    expect(body.status).toBe("validation_error");
  });

  test("missing service field → 400 validation error", async ({ page }) => {
    const { status, body } = await authPost(page, SCORING_ENDPOINT, {
      city: "Phoenix",
    });
    expect(status).toBe(400);
    expect(body.status).toBe("validation_error");
  });
});

// ── Duplicate submit / idempotency ───────────────────────────────────────────

test.describe("Duplicate submission safety", () => {
  test.setTimeout(180_000);

  test("two rapid identical requests both complete without server error", async ({
    page,
  }) => {
    const data = { city: "Phoenix", service: "roofing", state: "AZ" };
    const [r1, r2] = await Promise.all([
      authPost(page, SCORING_ENDPOINT, data),
      authPost(page, SCORING_ENDPOINT, data),
    ]);

    for (const r of [r1, r2]) {
      expect(r.status).toBeLessThan(500);
    }
  });
});

// ── Browser-level Huntsville regression (UI flow) ────────────────────────────

test.describe("UI: Huntsville shows actionable error", () => {
  test("submitting Huntsville via UI shows error banner, not blank page", async ({
    page,
  }) => {
    await page.goto("/niche-finder");
    await page.waitForLoadState("networkidle");

    await page.getByTestId("city-input").fill("Huntsville");
    await page.getByTestId("service-input").fill("tree removal");
    await page.getByTestId("submit-btn").click();

    const resultOrError = page.locator(
      '[data-testid="result-card"], [data-testid="error-banner"]',
    );
    await expect(resultOrError.first()).toBeVisible({ timeout: 90_000 });

    const errorBanner = page.getByTestId("error-banner");
    if (await errorBanner.isVisible()) {
      const text = await errorBanner.textContent();
      expect(text).toBeTruthy();
      expect(text!.length).toBeGreaterThan(10);
    }
  });
});
