import { expect, test, type Page } from "@playwright/test";
import flow from "../../../scripts/qa/flows/consumer.json";
import { signIn } from "./helpers/auth";

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

for (const viewport of flow.viewports) {
  test.describe(`consumer visual qa ${viewport.name}`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    for (const route of flow.routes) {
      test(`${route.name} renders without visual shell regressions`, async ({
        page,
      }, testInfo) => {
        test.info().annotations.push({
          type: "visual-baseline",
          description:
            "Snapshot baselines are intentionally generated in a stable local or CI renderer with --update-snapshots.",
        });

        if (route.requiresAuth) {
          await signIn(page, { expectLandOn: /\/(reports|$)/ });
        }

        await page.goto(route.path);
        await settlePage(page);
        await expect(page).toHaveURL(new RegExp(`${route.expectedPath}(\\?|$)`));
        await page.screenshot({
          path: testInfo.outputPath(
            `${artifactName(route.path, viewport.name)}-pass-review.png`,
          ),
          fullPage: true,
        });
        await expect(page).toHaveScreenshot(
          `consumer-${route.name}-${viewport.name}.png`,
          {
            fullPage: true,
            maxDiffPixelRatio: 0.02,
          },
        );
      });
    }
  });
}
