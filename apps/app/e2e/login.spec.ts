import { test, expect } from "@playwright/test";

test.describe("Password Login", () => {
  test("shows error for invalid credentials", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email address").fill("nobody@example.com");
    await page.getByLabel("Password").fill("wrongpassword");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page.getByText(/invalid/i)).toBeVisible({ timeout: 10_000 });
    await expect(page).toHaveURL(/\/login/);
  });

  test("successful login redirects to home", async ({ page }) => {
    const email = process.env.E2E_AUTH_EMAIL;
    const password = process.env.E2E_AUTH_PASSWORD;

    test.skip(!email || !password, "E2E_AUTH_EMAIL / E2E_AUTH_PASSWORD not set");

    await page.goto("/login");
    await page.getByLabel("Email address").fill(email!);
    await page.getByLabel("Password").fill(password!);
    await page.getByRole("button", { name: "Sign in" }).click();

    await page.waitForURL("**/", { timeout: 15_000 });
    await expect(page).not.toHaveURL(/\/login/);
  });
});
