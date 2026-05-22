import { expect, test, type Page, type Route } from "@playwright/test";
import { hasE2ECredentials, signIn, type SignInOptions } from "./helpers/auth";

const targetPath =
  "/competitor-intel?city=Boise&state=ID&service=roofing&place_id=place.boise&dataforseo_location_code=1027744";
const reportPath = "/competitor-intel?report_id=11111111-1111-4111-8111-111111111111";
const cbsaPath = "/competitor-intel?cbsa_code=14260&service=roofing";

const readyEnvelope = {
  status: "ready_to_run",
  message: "No durable competitor facts found yet for this market.",
};

const aggregateEnvelope = {
  status: "aggregate_only",
  aggregate: {
    city: "Boise",
    state: "ID",
    service: "roofing",
    market_ledger: [
      { label: "Market", value: "Boise, ID" },
      { label: "Service", value: "roofing" },
    ],
    summary_metrics: [
      { label: "Avg top-5 DA", value: 23, detail: "Aggregate organic signal" },
      { label: "Top-3 reviews", value: 41, detail: "Local pack aggregate" },
    ],
    coverage: [
      {
        label: "Organic SERP competitors",
        status: "partial",
        detail: "Aggregate top-5 facts only.",
      },
      {
        label: "Local pack competitors",
        status: "missing",
        detail: "Listing rows pending.",
      },
    ],
  },
};

const dossierEnvelope = {
  status: "dossier",
  dossier: {
    report_id: "11111111-1111-4111-8111-111111111111",
    city: "Boise",
    state: "ID",
    service: "roofing",
    generated_at: "2026-05-22T00:00:00.000Z",
    market_ledger: [
      { label: "Market", value: "Boise, ID" },
      { label: "Service", value: "roofing" },
      { label: "Report", value: null },
    ],
    summary_metrics: [
      { label: "Avg DA", value: 24 },
      { label: "Schema adoption", value: "10%" },
    ],
    organic_competitors: [
      {
        rank: 1,
        domain: "boiseroofpros.com",
        title: "Boise Roof Pros",
        domain_authority: 24,
        backlink_count: 126,
        referring_domains: 22,
        lighthouse_score: 74,
        schema_adoption: false,
        weaknesses: ["No LocalBusiness schema", "Thin city page"],
      },
    ],
    local_pack_competitors: [
      {
        rank: 1,
        name: "Boise Roof Pros",
        rating: 4.6,
        review_count: 48,
        gbp_completeness: 0.72,
        weaknesses: ["Low review velocity"],
      },
    ],
    win_plan: [
      {
        title: "Ship LocalBusiness schema",
        play: "Add LocalBusiness and Service schema to the primary service page.",
        estimated_impact: "High",
        rationale: "The visible organic competitor does not expose local schema.",
      },
    ],
    coverage: [
      {
        label: "Organic SERP competitors",
        status: "available",
        detail: "1 ranked competitor.",
      },
      {
        label: "GBP post history",
        status: "missing",
        detail: "Not returned by the provider.",
      },
    ],
  },
};

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function mockCompetitorRead(page: Page, body: unknown) {
  const seen: URL[] = [];
  await page.route("**/api/competitor-intel?**", async (route) => {
    seen.push(new URL(route.request().url()));
    await fulfillJson(route, body);
  });
  return seen;
}

async function mockCompetitorRun(
  page: Page,
  body: unknown,
  status = 200,
) {
  const seen: unknown[] = [];
  await page.route("**/api/competitor-intel/runs", async (route) => {
    seen.push(route.request().postDataJSON());
    await fulfillJson(route, body, status);
  });
  return seen;
}

async function signInForCompetitorIntel(
  page: Page,
  options: SignInOptions = {},
) {
  test.skip(!hasE2ECredentials(), "Set E2E_AUTH_EMAIL/E2E_AUTH_PASSWORD for auth E2E.");
  try {
    await signIn(page, { expectLandOn: /\/(reports|$)/, ...options });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (/invalid login credentials|\[login\] sign-in failed/i.test(message)) {
      test.skip(
        true,
        "Configured E2E auth credentials were rejected by Supabase.",
      );
    }
    throw error;
  }
}

async function skipIfSignedInPersonaIsFree(page: Page) {
  const upgrade = page.getByRole("heading", {
    name: /competitor intel needs a paid plan/i,
  });
  if (await upgrade.isVisible({ timeout: 1_500 }).catch(() => false)) {
    test.skip(
      true,
      "Signed-in E2E persona is free; paid Competitor Intel states are covered by mocked component/API tests.",
    );
  }
}

async function openPaidCompetitorIntel(
  page: Page,
  path: string,
  readBody: unknown = readyEnvelope,
) {
  const readRequests = await mockCompetitorRead(page, readBody);
  await signInForCompetitorIntel(page);
  await page.goto(path);
  await expect(page.getByRole("heading", { name: "Competitor Intel" })).toBeVisible();
  await skipIfSignedInPersonaIsFree(page);
  return readRequests;
}

async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() => {
    const root = document.documentElement;
    return root.scrollWidth - root.clientWidth;
  });
  expect(overflow).toBeLessThanOrEqual(1);
}

test.describe("Competitor Intel route", () => {
  test("unauthenticated direct links redirect to login", async ({ page }) => {
    await page.goto(targetPath);
    await page.waitForURL(/\/login/, { timeout: 10_000 });

    await expect(page).toHaveURL(/\/login/);
  });

  test("authenticated direct links preserve route params after login", async ({
    page,
  }) => {
    test.skip(!hasE2ECredentials(), "Set E2E_AUTH_EMAIL/E2E_AUTH_PASSWORD for auth E2E.");

    await signInForCompetitorIntel(page, {
      loginQuery: `?next=${encodeURIComponent(targetPath)}`,
      expectLandOn: (url) =>
        url.pathname === "/competitor-intel" &&
        url.searchParams.get("city") === "Boise" &&
        url.searchParams.get("state") === "ID" &&
        url.searchParams.get("service") === "roofing",
    });

    await expect(page.getByRole("heading", { name: "Competitor Intel" })).toBeVisible();
  });

  for (const [label, path, expectedParams] of [
    ["city/state/service", targetPath, { city: "Boise", service: "roofing" }],
    ["report_id", reportPath, { report_id: "11111111-1111-4111-8111-111111111111" }],
    ["cbsa/service", cbsaPath, { cbsa_code: "14260", service: "roofing" }],
  ] as const) {
    test(`paid direct link loads durable state for ${label}`, async ({ page }) => {
      const readRequests = await openPaidCompetitorIntel(page, path, aggregateEnvelope);

      await expect
        .poll(() => readRequests.length, { timeout: 10_000 })
        .toBe(1);
      for (const [key, value] of Object.entries(expectedParams)) {
        expect(readRequests[0].searchParams.get(key)).toBe(value);
      }
      await expect(
        page.getByRole("heading", { name: /market-level evidence is available/i }),
      ).toBeVisible();
    });
  }

  test("free persona sees upgrade state without competitor details", async ({
    page,
  }) => {
    await signInForCompetitorIntel(page);
    await page.goto(targetPath);

    const upgrade = page.getByRole("heading", {
      name: /competitor intel needs a paid plan/i,
    });
    if (!(await upgrade.isVisible({ timeout: 2_000 }).catch(() => false))) {
      test.skip(true, "Signed-in E2E persona is paid; free upgrade state is covered by unit/component tests.");
    }

    await expect(upgrade).toBeVisible();
    await expect(page.getByRole("link", { name: /view plans/i })).toBeVisible();
    await expect(page.getByText("boiseroofpros.com")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: /organic competitors/i })).toHaveCount(0);
  });

  test("ready state confirms exactly one 2-scan run", async ({ page }) => {
    const runRequests = await mockCompetitorRun(page, {
      status: "running",
      run_id: "competitor-run-1",
      message: "Queued",
    });
    await openPaidCompetitorIntel(page, targetPath, readyEnvelope);

    await expect(page.getByText("2 scans")).toBeVisible();
    await page.getByRole("button", { name: /run competitor intel/i }).click();
    await expect(
      page.getByRole("alertdialog", { name: /confirm 2-scan run/i }),
    ).toBeVisible();
    await page.getByRole("button", { name: /confirm run/i }).dblclick();

    await expect
      .poll(() => runRequests.length, { timeout: 10_000 })
      .toBe(1);
    expect(runRequests[0]).toMatchObject({
      city: "Boise",
      state: "ID",
      service: "roofing",
      scan_cost: 2,
    });
    await expect(
      page.getByRole("heading", { name: /competitor intel is in progress/i }),
    ).toBeVisible();
  });

  test("quota-blocked and upstream failures surface error states", async ({
    page,
  }) => {
    await mockCompetitorRun(
      page,
      {
        status: "quota_exceeded",
        message: "You need 2 scans remaining to run competitor intel.",
        required_scans: 2,
      },
      429,
    );
    await openPaidCompetitorIntel(page, targetPath, readyEnvelope);

    await page.getByRole("button", { name: /run competitor intel/i }).click();
    await page.getByRole("button", { name: /confirm run/i }).click();

    await expect(
      page.getByRole("heading", { name: /competitor intel is unavailable/i }),
    ).toBeVisible();
    await expect(
      page.getByText("You need 2 scans remaining to run competitor intel."),
    ).toBeVisible();
    await expect(page.getByText("boiseroofpros.com")).toHaveCount(0);
  });

  test("aggregate-only state omits dossier-only sections", async ({ page }) => {
    await openPaidCompetitorIntel(page, targetPath, aggregateEnvelope);

    await expect(page.getByRole("heading", { name: /market ledger/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /summary metrics/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /coverage/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /organic competitors/i })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: /win plan/i })).toHaveCount(0);
  });

  test("dossier reload renders all sections without null clutter or extra charges", async ({
    page,
  }) => {
    const runRequests = await mockCompetitorRun(page, {
      status: "running",
      run_id: "should-not-run",
    });
    await openPaidCompetitorIntel(page, reportPath, dossierEnvelope);

    await expect(page.getByRole("heading", { name: /market ledger/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /summary metrics/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /organic competitors/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /local-pack competitors/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /win plan/i })).toBeVisible();
    await expect(page.getByText("boiseroofpros.com")).toBeVisible();
    await expect(page.getByText("GBP post history")).toBeVisible();
    await expect(page.getByText(/^null$/i)).toHaveCount(0);
    expect(runRequests).toHaveLength(0);
  });

  test("invalid target disables the run action", async ({ page }) => {
    await signInForCompetitorIntel(page);
    await page.goto("/competitor-intel");
    await expect(page.getByRole("heading", { name: "Competitor Intel" })).toBeVisible();
    await skipIfSignedInPersonaIsFree(page);

    await expect(
      page.getByText(/open this route with report_id, or city and service/i),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: /run competitor intel/i })).toBeDisabled();
  });

  test("mobile dossier layout keeps actions visible without horizontal overflow", async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await openPaidCompetitorIntel(page, targetPath, dossierEnvelope);
    await expectNoHorizontalOverflow(page);
    await expect(page.getByRole("heading", { name: /organic competitors/i })).toBeVisible();

    await page.screenshot({
      path: testInfo.outputPath("competitor-intel-dossier-mobile-review.png"),
      fullPage: true,
    });
  });

  test("mobile ready confirmation keeps both modal actions visible", async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await mockCompetitorRun(page, { status: "running", run_id: "run-mobile" });
    await openPaidCompetitorIntel(page, targetPath, readyEnvelope);
    await page.getByRole("button", { name: /run competitor intel/i }).click();

    const dialog = page.getByRole("alertdialog", { name: /confirm 2-scan run/i });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("button", { name: /cancel/i })).toBeVisible();
    await expect(dialog.getByRole("button", { name: /confirm run/i })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await page.keyboard.press("Escape");
    await expect(dialog).toBeVisible();

    await page.screenshot({
      path: testInfo.outputPath("competitor-intel-ready-mobile-review.png"),
      fullPage: true,
    });
  });
});
