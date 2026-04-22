import { test, expect } from "@playwright/test";
import { signIn } from "./helpers/auth";

test.describe("Reports page smoke test", () => {
  test("reports page renders heading and table after sign-in", async ({
    page,
  }) => {
    await signIn(page, { expectLandOn: /\/(reports|$)/ });
    await page.goto("/reports");
    await page.waitForLoadState("networkidle");

    await expect(
      page.getByRole("heading", { name: /^reports$/i }),
    ).toBeVisible({ timeout: 10_000 });

    await expect(page.getByText(/showing \d+ of/i)).toBeVisible({
      timeout: 10_000,
    });
  });

  test("niche finder page renders after sign-in", async ({ page }) => {
    await signIn(page, { expectLandOn: /\/(reports|$)/ });
    await page.goto("/niche-finder");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText(/find a niche/i)).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByTestId("submit-btn")).toBeVisible();
  });

  test("home page renders after sign-in", async ({ page }) => {
    await signIn(page, { expectLandOn: /\/(reports|$)/ });
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    await expect(page.locator(".sidebar, [data-testid='sidebar']").first()).toBeVisible({ timeout: 10_000 });
  });
});
