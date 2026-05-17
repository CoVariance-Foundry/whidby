import { expect, test, type Page } from "@playwright/test";
import flow from "../../../scripts/qa/flows/admin.json";

function artifactName(routePath: string, viewportName: string): string {
  const routeSlug =
    routePath === "/"
      ? "root"
      : routePath.replace(/^\/+/, "").replace(/[^a-zA-Z0-9-]+/g, "-");

  return `admin-route-${routeSlug}-${viewportName}`;
}

async function settlePage(page: Page): Promise<void> {
  await expect(page.locator("body")).toBeVisible();
  await page.waitForLoadState("domcontentloaded");
  await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => {
    // Redirect-stable auth pages may still have background client activity.
  });
}

for (const viewport of flow.viewports) {
  test.describe(`admin visual qa ${viewport.name}`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    for (const route of flow.routes) {
      test(`${route.name} renders without visual shell regressions`, async ({
        page,
      }, testInfo) => {
        test.info().annotations.push({
          type: "visual-baseline",
          description:
            "Admin protected routes are captured as unauthenticated redirect-stable pages until a shared admin auth helper exists.",
        });

        await page.goto(route.path);

        if (route.requiresAuth) {
          await page.waitForURL("**/login**", { timeout: 10_000 });
        }

        await settlePage(page);
        await expect(page).toHaveURL(new RegExp(`${route.expectedPath}(\\?|$)`));
        await page.screenshot({
          path: testInfo.outputPath(
            `${artifactName(route.path, viewport.name)}-pass-review.png`,
          ),
          fullPage: true,
        });
        await expect(page).toHaveScreenshot(
          `admin-${route.name}-${viewport.name}.png`,
          {
            fullPage: true,
            maxDiffPixelRatio: 0.02,
          },
        );
      });
    }
  });
}
