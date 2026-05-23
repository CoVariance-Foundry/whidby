import fs from "fs";
import path from "path";
import { expect, test, type Page, type Route } from "@playwright/test";
import { signIn } from "./helpers/auth";

type Tier = "free" | "plus" | "pro";

type TierAccount = {
  email?: string;
  password?: string;
};

type TierScenario = {
  tier: Tier;
  label: "Free" | "Plus" | "Pro";
  reportLimit: number;
  account: TierAccount;
  verifyUpgradePath: (page: Page, recorder: BillingRecorder) => Promise<void>;
};

type BillingRecorder = {
  checkoutPlanKeys: string[];
  portalHits: number;
};

const repoRoot = path.resolve(__dirname, "../../..");
loadDotEnv(path.join(repoRoot, ".env"));
loadDotEnv(path.resolve(__dirname, "../.env.local"));

const scenarios: TierScenario[] = [
  {
    tier: "free",
    label: "Free",
    reportLimit: 0,
    account: accountFromEnv({
      emailKeys: ["E2E_FREE_EMAIL", "WHIDBY_TEST_USER_EMAIL"],
      passwordKeys: ["E2E_FREE_PASSWORD", "WHIDBY_TEST_USER_PASSWORD"],
      defaultEmail: "user-test@widby.dev",
    }),
    verifyUpgradePath: async (page, recorder) => {
      await expect(page.getByRole("button", { name: /upgrade to plus/i })).toBeVisible();
      await expect(page.getByRole("button", { name: /upgrade to pro/i })).toBeVisible();

      await page.getByRole("button", { name: /upgrade to plus/i }).click();
      await page.waitForURL(/\/settings\?billing=success&mock_checkout=plus$/);
      expect(recorder.checkoutPlanKeys).toEqual(["plus"]);
    },
  },
  {
    tier: "plus",
    label: "Plus",
    reportLimit: 10,
    account: accountFromEnv({
      emailKeys: ["E2E_PLUS_EMAIL"],
      passwordKeys: ["E2E_PLUS_PASSWORD"],
    }),
    verifyUpgradePath: async (page, recorder) => {
      await expect(page.getByRole("button", { name: /change in stripe/i })).toBeVisible();
      await expect(page.getByRole("button", { name: /manage downgrade/i })).toBeVisible();
      await expect(page.getByRole("button", { name: /cancel in stripe|manage in stripe/i })).toBeVisible();

      await verifyPortalPathOrMissingBillingProfile(page, recorder, /change in stripe/i);
    },
  },
  {
    tier: "pro",
    label: "Pro",
    reportLimit: 50,
    account: accountFromEnv({
      emailKeys: ["E2E_PRO_EMAIL", "WHIDBY_BETA_LUKE_EMAIL"],
      passwordKeys: ["E2E_PRO_PASSWORD", "WHIDBY_BETA_LUKE_PASSWORD"],
      defaultEmail: "lm13vand@gmail.com",
    }),
    verifyUpgradePath: async (page, recorder) => {
      await expect(page.getByRole("button", { name: /change in stripe/i })).toBeVisible();
      await expect(page.getByRole("button", { name: /manage downgrade/i })).toBeVisible();
      await expect(page.getByRole("button", { name: /cancel in stripe|manage in stripe/i })).toBeVisible();

      await verifyPortalPathOrMissingBillingProfile(page, recorder, /manage downgrade/i);
    },
  },
];

test.describe("tier upgrade paths", () => {
  test.describe.configure({ mode: "serial" });

  for (const scenario of scenarios) {
    test(`${scenario.label} account exposes the expected upgrade path`, async ({
      page,
    }) => {
      test.skip(
        !scenario.account.email || !scenario.account.password,
        `requires ${scenario.tier.toUpperCase()} tier credentials. Set E2E_${scenario.tier.toUpperCase()}_EMAIL and E2E_${scenario.tier.toUpperCase()}_PASSWORD.`,
      );

      const recorder = await stubBillingRoutes(page);

      await signIn(page, {
        email: scenario.account.email,
        password: scenario.account.password,
        loginQuery: "?next=%2Fsettings",
        expectLandOn: /\/settings(\?|$)/,
        timeoutMs: 20_000,
      });
      await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => {
        // Authenticated settings pages can keep analytics requests open.
      });

      await expect(
        page.getByRole("heading", { name: /account & billing/i }),
      ).toBeVisible({ timeout: 10_000 });
      await expect(page.getByRole("heading", { name: scenario.label }).first()).toBeVisible();
      await expect(
        page.getByLabel(new RegExp(`Reports used \\d+ of ${scenario.reportLimit}`)),
      ).toBeVisible();
      await expect(page.getByText(/choose your plan/i)).toBeVisible();

      await scenario.verifyUpgradePath(page, recorder);
    });
  }
});

function accountFromEnv({
  emailKeys,
  passwordKeys,
  defaultEmail,
}: {
  emailKeys: string[];
  passwordKeys: string[];
  defaultEmail?: string;
}): TierAccount {
  return {
    email: envFirst(emailKeys) ?? defaultEmail,
    password: envFirst(passwordKeys),
  };
}

function envFirst(keys: string[]): string | undefined {
  for (const key of keys) {
    const value = process.env[key];
    if (value) return value;
  }
  return undefined;
}

function loadDotEnv(filePath: string): void {
  if (!fs.existsSync(filePath)) return;

  for (const line of fs.readFileSync(filePath, "utf8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) continue;

    const [rawKey, ...rawValueParts] = trimmed.split("=");
    const key = rawKey.trim();
    let value = rawValueParts.join("=").trim();
    if (
      value.length >= 2 &&
      ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'")))
    ) {
      value = value.slice(1, -1);
    }

    if (key && process.env[key] === undefined) {
      process.env[key] = value;
    }
  }
}

async function stubBillingRoutes(page: Page): Promise<BillingRecorder> {
  const recorder: BillingRecorder = {
    checkoutPlanKeys: [],
    portalHits: 0,
  };

  await page.route("**/api/billing/checkout", async (route) => {
    const planKey = parsePlanKey(route);
    recorder.checkoutPlanKeys.push(planKey);
    const origin = new URL(route.request().url()).origin;

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "success",
        url: `${origin}/settings?billing=success&mock_checkout=${planKey}`,
      }),
    });
  });

  await page.route("**/api/billing/portal", async (route) => {
    recorder.portalHits += 1;
    const origin = new URL(route.request().url()).origin;

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "success",
        url: `${origin}/settings?billing=success&mock_portal=1`,
      }),
    });
  });

  return recorder;
}

function parsePlanKey(route: Route): string {
  const payload = route.request().postDataJSON() as { plan_key?: unknown } | null;
  return typeof payload?.plan_key === "string" ? payload.plan_key : "<missing>";
}

async function verifyPortalPathOrMissingBillingProfile(
  page: Page,
  recorder: BillingRecorder,
  buttonName: RegExp,
): Promise<void> {
  const hasBillingProfile = await page
    .getByText(/payment details are managed in stripe/i)
    .isVisible();

  await page.getByRole("button", { name: buttonName }).first().click();

  if (hasBillingProfile) {
    await page.waitForURL(/\/settings\?billing=success&mock_portal=1$/);
    expect(recorder.portalHits).toBe(1);
    return;
  }

  await expect(page.getByRole("status")).toHaveText(
    /choose plus or pro first to create a billing profile/i,
  );
  expect(recorder.portalHits).toBe(0);
}
