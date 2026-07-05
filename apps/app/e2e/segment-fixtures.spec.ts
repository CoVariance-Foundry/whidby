import { test, expect, type Page } from "@playwright/test";
import { signIn } from "./helpers/auth";

type SegmentFixture = {
  segment: string;
  emailEnv: string;
  defaultEmail: string;
  passwordEnv: string;
  expectedPath: string;
  heading: RegExp;
  requiresExploreApi?: boolean;
};

const commonPassword = process.env.WHIDBY_SEGMENT_FIXTURE_PASSWORD;
const hasExploreApi = Boolean(process.env.NEXT_PUBLIC_API_URL?.trim());

const fixtures: SegmentFixture[] = [
  {
    segment: "find_first",
    emailEnv: "WHIDBY_SEGMENT_FIND_FIRST_EMAIL",
    defaultEmail: "segment-find-first@widby.dev",
    passwordEnv: "WHIDBY_SEGMENT_FIND_FIRST_PASSWORD",
    expectedPath: "/",
    heading: /^dashboard$/i,
  },
  {
    segment: "scale",
    emailEnv: "WHIDBY_SEGMENT_SCALE_EMAIL",
    defaultEmail: "segment-scale@widby.dev",
    passwordEnv: "WHIDBY_SEGMENT_SCALE_PASSWORD",
    expectedPath: "/strategies",
    heading: /^strategy path$/i,
  },
  {
    segment: "coach_agency",
    emailEnv: "WHIDBY_SEGMENT_COACH_AGENCY_EMAIL",
    defaultEmail: "segment-coach-agency@widby.dev",
    passwordEnv: "WHIDBY_SEGMENT_COACH_AGENCY_PASSWORD",
    expectedPath: "/agency",
    heading: /^qualify territories in one batch\.$/i,
  },
  {
    segment: "researching",
    emailEnv: "WHIDBY_SEGMENT_RESEARCHING_EMAIL",
    defaultEmail: "segment-researching@widby.dev",
    passwordEnv: "WHIDBY_SEGMENT_RESEARCHING_PASSWORD",
    expectedPath: "/explore",
    heading: /^cities & service data$/i,
    requiresExploreApi: true,
  },
];

function credentialsFor(fixture: SegmentFixture) {
  const password = process.env[fixture.passwordEnv] ?? commonPassword;
  if (!password) return null;
  return {
    email: process.env[fixture.emailEnv] ?? fixture.defaultEmail,
    password,
  };
}

async function blockFreshPaidApis(page: Page) {
  await page.route("**/api/agent/scoring", (route) =>
    route.fulfill({ status: 418, body: "blocked by segment fixture smoke" }),
  );
  await page.route("**/api/strategies/runs", (route) =>
    route.fulfill({ status: 418, body: "blocked by segment fixture smoke" }),
  );
  await page.route("**/api/competitor-intel/runs", (route) =>
    route.fulfill({ status: 418, body: "blocked by segment fixture smoke" }),
  );
}

async function assertSegmentSurface(fixture: SegmentFixture, page: Page) {
  if (fixture.segment !== "scale") return;

  await expect(page.getByLabel("B2 strategy path rail")).toBeVisible();
  await expect(page.getByText("Easy Win").first()).toBeVisible();
  await expect(page.getByText("GBP Blitz").first()).toBeVisible();
  await expect(page.getByText("Expand & Conquer").first()).toBeVisible();
  await expect(page.getByText("Keyword Hijack").first()).toBeVisible();
  await expect(page.getByText("Portfolio Builder").first()).toBeVisible();
  await expect(page.getByText("Cash Cow")).toHaveCount(0);
  await expect(page.getByText("Blue Ocean")).toHaveCount(0);
  await page.screenshot({
    path: "test-results/wave4-scale-strategy-path.png",
    fullPage: true,
  });
}

test.describe("seeded segment fixtures", () => {
  for (const fixture of fixtures) {
    test(`${fixture.segment} routes to ${fixture.expectedPath}`, async ({ page }) => {
      const credentials = credentialsFor(fixture);
      // REASON: Segment fixture smoke requires live seeded Supabase users.
      test.skip(
        !credentials,
        `requires ${fixture.passwordEnv} or WHIDBY_SEGMENT_FIXTURE_PASSWORD`,
      );
      if (!credentials) {
        return;
      }
      const missingExploreApi = Boolean(fixture.requiresExploreApi && !hasExploreApi);
      // REASON: /explore loads backend data server-side, outside Playwright route interception.
      test.skip(
        missingExploreApi,
        "requires NEXT_PUBLIC_API_URL pointing at a running Explore API backend",
      );
      if (missingExploreApi) {
        return;
      }

      await blockFreshPaidApis(page);
      await signIn(page, {
        email: credentials.email,
        password: credentials.password,
        expectLandOn: (url) => url.pathname === fixture.expectedPath,
      });
      await page.waitForLoadState("networkidle");

      await expect(
        page.getByRole("heading", { name: fixture.heading }).first(),
      ).toBeVisible({ timeout: 10_000 });
      await assertSegmentSurface(fixture, page);
    });
  }
});
