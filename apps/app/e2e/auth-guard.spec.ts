import { test, expect } from "@playwright/test";

/**
 * Baseline auth-guard coverage for the consumer app. The deeper next=
 * round-trip and open-redirect rejection suite lives in next-param.spec.ts.
 */
test.describe("Auth Guard", () => {
  test("unauthenticated visit to / redirects to /login", async ({ page }) => {
    await page.goto("/");
    await page.waitForURL("**/login**", { timeout: 10_000 });
    await expect(page).toHaveURL(/\/login/);
  });

  test("unauthenticated visit to /reports redirects to /login", async ({
    page,
  }) => {
    await page.goto("/reports");
    await page.waitForURL("**/login**", { timeout: 10_000 });
    await expect(page).toHaveURL(/\/login/);
  });

  test("login page renders the email + password form", async ({ page }) => {
    await page.goto("/login");
    await expect(
      page.getByRole("heading", { name: "Widby", exact: true }),
    ).toBeVisible();
    await expect(page.getByPlaceholder("you@example.com")).toBeVisible();
    await expect(page.getByPlaceholder("••••••••")).toBeVisible();
    await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
  });

  test("login inputs have correct HTML types and are required", async ({
    page,
  }) => {
    await page.goto("/login");
    const emailInput = page.getByPlaceholder("you@example.com");
    await expect(emailInput).toHaveAttribute("type", "email");
    await expect(emailInput).toHaveAttribute("required", "");

    const passwordInput = page.getByPlaceholder("••••••••");
    await expect(passwordInput).toHaveAttribute("type", "password");
    await expect(passwordInput).toHaveAttribute("required", "");
  });
});
