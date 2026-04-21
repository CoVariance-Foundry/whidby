import { test, expect } from "@playwright/test";

test.describe("Foundation flow", () => {
  test("home page renders dashboard sections", async ({ page }) => {
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: /good work/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /open niche finder/i }),
    ).toBeVisible();
  });

  test("niche finder command center loads and switches tabs", async ({
    page,
  }) => {
    await page.goto("/niche-finder");
    await expect(
      page.getByRole("heading", { name: /score a niche/i }),
    ).toBeVisible();
    await page.getByRole("tab", { name: /strategy/i }).click();
    await expect(
      page.getByText(/aggregator|pack, vulnerable/i),
    ).toBeVisible();
  });

  test("reports page filters by archetype chip", async ({ page }) => {
    await page.goto("/reports");
    await expect(
      page.getByRole("heading", { name: /^reports$/i }),
    ).toBeVisible();
    await expect(page.getByText(/showing \d+ of/i)).toBeVisible();
  });
});
