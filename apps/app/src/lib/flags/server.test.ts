import { describe, expect, it } from "vitest";
import { PRODUCT_FLAGS } from "./product-flags";
import { getServerFeatureFlag } from "./server";

describe("server feature flags", () => {
  it("falls back to the secure default when PostHog is not configured", async () => {
    const originalKey = process.env.NEXT_PUBLIC_POSTHOG_KEY;
    delete process.env.NEXT_PUBLIC_POSTHOG_KEY;
    const enabled = await getServerFeatureFlag(
      "report_quota_enforcement_enabled",
      true,
      "user-1",
    );
    expect(enabled).toBe(true);
    if (originalKey) {
      process.env.NEXT_PUBLIC_POSTHOG_KEY = originalKey;
    }
  });

  it("defines the initial product rollout flags", () => {
    expect(PRODUCT_FLAGS.userManagementEnabled).toMatchObject({
      key: "user_management_enabled",
      defaultValue: false,
    });
    expect(PRODUCT_FLAGS.billingCheckoutEnabled.defaultValue).toBe(true);
    expect(PRODUCT_FLAGS.reportQuotaEnforcementEnabled.defaultValue).toBe(true);
    expect(PRODUCT_FLAGS.freshReportGenerationEnabled.defaultValue).toBe(true);
    expect(PRODUCT_FLAGS.cachedReportsEnabled.defaultValue).toBe(true);
  });

  it("reads hyphenated feature flag keys from underscore env vars", async () => {
    process.env.BILLING_CHECKOUT_ENABLED = "true";
    const enabled = await getServerFeatureFlag(
      "billing-checkout-enabled",
      false,
      "user-1",
    );
    expect(enabled).toBe(true);
    delete process.env.BILLING_CHECKOUT_ENABLED;
  });
});
