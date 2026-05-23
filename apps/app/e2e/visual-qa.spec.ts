import { expect, test, type Page } from "@playwright/test";
import flow from "../../../scripts/qa/flows/consumer.json";
import { hasE2ECredentials, signIn } from "./helpers/auth";

const consumerFlow = flow as typeof flow & { authLandingPattern?: string };
const authLandingPattern = new RegExp(
  consumerFlow.authLandingPattern ?? "/(reports|$)",
);

function artifactName(routePath: string, viewportName: string): string {
  const routeSlug =
    routePath === "/"
      ? "root"
      : routePath.replace(/^\/+/, "").replace(/[^a-zA-Z0-9-]+/g, "-");

  return `consumer-route-${routeSlug}-${viewportName}`;
}

async function settlePage(page: Page): Promise<void> {
  await expect(page.locator("body")).toBeVisible();
  await page.waitForLoadState("domcontentloaded");
  await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => {
    // Some authenticated pages may keep analytics or data requests open.
  });
}

async function mockCompetitorIntelVisualState(page: Page, routePath: string): Promise<void> {
  if (!routePath.startsWith("/competitor-intel")) return;

  await page.route("**/api/competitor-intel?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
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
            { label: "Avg top-5 DA", value: 23 },
            { label: "Top-3 reviews", value: 41 },
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
      }),
    });
  });
}

async function signInForVisualQa(page: Page): Promise<void> {
  test.skip(!hasE2ECredentials(), "Set E2E_AUTH_EMAIL/E2E_AUTH_PASSWORD for auth visual QA.");
  try {
    await signIn(page, { expectLandOn: authLandingPattern });
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

for (const viewport of flow.viewports) {
  test.describe(`consumer visual qa ${viewport.name}`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    for (const route of flow.routes) {
      test(`${route.name} renders without visual shell regressions`, async ({
        page,
      }, testInfo) => {
        test.info().annotations.push({
          type: "visual-artifact",
          description:
            "This smoke captures review screenshots. Baseline assertions should be enabled after stable snapshots are committed.",
        });

        if (route.requiresAuth) {
          await signInForVisualQa(page);
        }

        await mockCompetitorIntelVisualState(page, route.path);
        await page.goto(route.path);
        await settlePage(page);
        await expect(page).toHaveURL(new RegExp(`${route.expectedPath}(\\?|$)`));
        await page.screenshot({
          path: testInfo.outputPath(
            `${artifactName(route.path, viewport.name)}-pass-review.png`,
          ),
          fullPage: true,
        });
      });
    }
  });
}
