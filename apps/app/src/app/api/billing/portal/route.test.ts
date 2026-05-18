import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  createClient: vi.fn(),
  createAdminClient: vi.fn(),
  resolveEntitlementContext: vi.fn(),
  getServerFeatureFlag: vi.fn(),
  portalCreate: vi.fn(),
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: mocks.createClient,
}));

vi.mock("@/lib/supabase/admin", () => ({
  createAdminClient: mocks.createAdminClient,
}));

vi.mock("@/lib/account/entitlements", () => ({
  resolveEntitlementContext: mocks.resolveEntitlementContext,
}));

vi.mock("@/lib/flags/server", () => ({
  getServerFeatureFlag: mocks.getServerFeatureFlag,
}));

vi.mock("@/lib/billing/stripe", () => ({
  getStripeClient: () => ({
    billingPortal: { sessions: { create: mocks.portalCreate } },
  }),
}));

import { POST } from "./route";

describe("POST /api/billing/portal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.createClient.mockResolvedValue({});
    mocks.resolveEntitlementContext.mockResolvedValue({
      user: { id: "user-1", email: "owner@example.com" },
      entitlement: {
        account_id: "account-1",
        member_role: "owner",
        plan_key: "plus",
        monthly_report_limit: 10,
        subscription_status: "active",
        current_period_start: "2026-05-01T00:00:00.000Z",
        current_period_end: "2026-06-01T00:00:00.000Z",
      },
    });
    mocks.getServerFeatureFlag.mockResolvedValue(true);
    mocks.portalCreate.mockResolvedValue({ url: "https://stripe.test/portal" });
    mocks.createAdminClient.mockReturnValue({
      from: () => ({
        select: () => ({
          eq: () => ({
            maybeSingle: vi.fn().mockResolvedValue({
              data: { stripe_customer_id: "cus_123" },
              error: null,
            }),
          }),
        }),
      }),
    });
  });

  it("returns users to the settings page after the Stripe portal", async () => {
    const req = new Request("http://localhost:3002/api/billing/portal", {
      method: "POST",
    });

    const res = await POST(req as never);

    expect(res.status).toBe(200);
    expect(mocks.portalCreate).toHaveBeenCalledWith({
      customer: "cus_123",
      return_url: "http://localhost:3002/settings?billing=success",
    });
  });
});
