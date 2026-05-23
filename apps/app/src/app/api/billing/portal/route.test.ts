import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  createClient: vi.fn(),
  createAdminClient: vi.fn(),
  resolveEntitlementContext: vi.fn(),
  getServerFeatureFlag: vi.fn(),
  recordBillingOperationEvent: vi.fn(),
  portalCreate: vi.fn(),
  customerRow: { data: { stripe_customer_id: "cus_123" }, error: null } as unknown,
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

vi.mock("@/lib/billing/ops-log", () => ({
  errorToInternalMessage: (error: unknown) =>
    error instanceof Error ? error.message : String(error),
  recordBillingOperationEvent: mocks.recordBillingOperationEvent,
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
    mocks.recordBillingOperationEvent.mockResolvedValue(undefined);
    mocks.portalCreate.mockResolvedValue({ url: "https://stripe.test/portal" });
    mocks.customerRow = { data: { stripe_customer_id: "cus_123" }, error: null };
    mocks.createAdminClient.mockReturnValue({
      from: () => ({
        select: () => ({
          eq: () => ({
            maybeSingle: vi.fn().mockResolvedValue(mocks.customerRow),
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

  it("logs missing billing customers for admin review", async () => {
    mocks.customerRow = { data: null, error: null };
    const req = new Request("http://localhost:3002/api/billing/portal", {
      method: "POST",
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(404);
    expect(body.code).toBe("billing_customer_missing");
    expect(mocks.recordBillingOperationEvent).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        severity: "warning",
        event_type: "portal_customer_missing",
        source: "portal",
      }),
    );
  });

  it("logs Stripe portal failures and returns a sanitized error", async () => {
    mocks.portalCreate.mockRejectedValue(new Error("No configuration provided"));
    const req = new Request("http://localhost:3002/api/billing/portal", {
      method: "POST",
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(500);
    expect(body).toMatchObject({
      status: "unavailable",
      code: "billing_portal_unavailable",
      message: "Billing management could not open. Please try again or contact support.",
    });
    expect(body.message).not.toContain("configuration");
    expect(mocks.recordBillingOperationEvent).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        severity: "error",
        event_type: "portal_failed",
        internal_message: "No configuration provided",
      }),
    );
  });
});
