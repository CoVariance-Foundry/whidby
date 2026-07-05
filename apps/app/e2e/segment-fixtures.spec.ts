import { test, expect, type Page } from "@playwright/test";
import { signIn } from "./helpers/auth";

type SegmentFixture = {
  segment: string;
  emailEnv: string;
  defaultEmail: string;
  passwordEnv: string;
  expectedPath: string;
  heading: RegExp;
};

const commonPassword = process.env.WHIDBY_SEGMENT_FIXTURE_PASSWORD;

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
    heading: /^multi-market scan$/i,
  },
  {
    segment: "researching",
    emailEnv: "WHIDBY_SEGMENT_RESEARCHING_EMAIL",
    defaultEmail: "segment-researching@widby.dev",
    passwordEnv: "WHIDBY_SEGMENT_RESEARCHING_PASSWORD",
    expectedPath: "/explore",
    heading: /^cities & service data$/i,
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

test.describe("seeded segment fixtures", () => {
  for (const fixture of fixtures) {
    test(`${fixture.segment} routes to ${fixture.expectedPath}`, async ({ page }) => {
      const credentials = credentialsFor(fixture);
      // REASON: Segment fixture smoke requires live seeded Supabase users.
      test.skip(
        !credentials,
        `requires ${fixture.passwordEnv} or WHIDBY_SEGMENT_FIXTURE_PASSWORD`,
      );

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
    });
  }
});
