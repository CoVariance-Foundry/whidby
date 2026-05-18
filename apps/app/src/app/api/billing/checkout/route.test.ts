import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  createClient: vi.fn(),
  createAdminClient: vi.fn(),
  resolveEntitlementContext: vi.fn(),
  getServerFeatureFlag: vi.fn(),
  getPriceIdForPlan: vi.fn(),
  upsertBillingCustomer: vi.fn(),
  checkoutCreate: vi.fn(),
  customerCreate: vi.fn(),
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
  getPriceIdForPlan: mocks.getPriceIdForPlan,
  isPaidPlan: (value: unknown) => value === "plus" || value === "pro",
  getStripeClient: () => ({
    customers: { create: mocks.customerCreate },
    checkout: { sessions: { create: mocks.checkoutCreate } },
  }),
}));

vi.mock("@/lib/billing/sync-subscription", () => ({
  upsertBillingCustomer: mocks.upsertBillingCustomer,
}));

import { POST } from "./route";

describe("POST /api/billing/checkout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.createClient.mockResolvedValue({});
    mocks.resolveEntitlementContext.mockResolvedValue({
      user: { id: "user-1", email: "owner@example.com" },
      entitlement: {
        account_id: "account-1",
        member_role: "owner",
        plan_key: "free",
        monthly_report_limit: 0,
        subscription_status: "active",
        current_period_start: "2026-05-01T00:00:00.000Z",
        current_period_end: "2026-06-01T00:00:00.000Z",
      },
    });
    mocks.getServerFeatureFlag.mockResolvedValue(true);
    mocks.getPriceIdForPlan.mockReturnValue("price_plus");
    mocks.customerCreate.mockResolvedValue({ id: "cus_123" });
    mocks.upsertBillingCustomer.mockResolvedValue(undefined);
    mocks.checkoutCreate.mockResolvedValue({ url: "https://stripe.test/checkout" });
    mocks.createAdminClient.mockReturnValue({
      from: (table: string) => ({
        select: () => ({
          eq: () => ({
            maybeSingle: vi.fn().mockResolvedValue(
              table === "billing_customers"
                ? { data: null, error: null }
                : { data: null, error: null },
            ),
            in: () => ({
              maybeSingle: vi.fn().mockResolvedValue({ data: null, error: null }),
            }),
          }),
        }),
      }),
    });
  });

  it("returns settings success and cancel URLs to Stripe", async () => {
    const req = new Request("http://localhost:3002/api/billing/checkout", {
      method: "POST",
      body: JSON.stringify({ plan_key: "plus" }),
    });

    const res = await POST(req as never);

    expect(res.status).toBe(200);
    expect(mocks.checkoutCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        success_url: "http://localhost:3002/settings?billing=success",
        cancel_url: "http://localhost:3002/settings?billing=cancelled",
      }),
    );
  });
});
