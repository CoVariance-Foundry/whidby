import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  createClient: vi.fn(),
  createAdminClient: vi.fn(),
  resolveEntitlementContext: vi.fn(),
  getServerFeatureFlag: vi.fn(),
  getPriceIdForPlan: vi.fn(),
  upsertBillingCustomer: vi.fn(),
  findReusableCheckoutSession: vi.fn(),
  expireStaleOrCompetingCheckoutSessions: vi.fn(),
  reserveCheckoutSession: vi.fn(),
  completeCheckoutSessionReservation: vi.fn(),
  recordBillingOperationEvent: vi.fn(),
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

vi.mock("@/lib/billing/checkout-session", () => ({
  findReusableCheckoutSession: mocks.findReusableCheckoutSession,
  expireStaleOrCompetingCheckoutSessions: mocks.expireStaleOrCompetingCheckoutSessions,
  reserveCheckoutSession: mocks.reserveCheckoutSession,
  completeCheckoutSessionReservation: mocks.completeCheckoutSessionReservation,
}));

vi.mock("@/lib/billing/ops-log", () => ({
  errorToInternalMessage: (error: unknown) =>
    error instanceof Error ? error.message : String(error),
  recordBillingOperationEvent: mocks.recordBillingOperationEvent,
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
    mocks.findReusableCheckoutSession.mockResolvedValue(null);
    mocks.expireStaleOrCompetingCheckoutSessions.mockResolvedValue(undefined);
    mocks.reserveCheckoutSession.mockResolvedValue({
      id: "reservation-1",
      account_id: "account-1",
      user_id: "user-1",
      plan_key: "plus",
      status: "pending",
      stripe_checkout_session_id: null,
      stripe_checkout_url: null,
      expires_at: "2026-05-01T00:30:00.000Z",
      idempotency_key: "billing-checkout:account-1:plus:reservation-1",
    });
    mocks.completeCheckoutSessionReservation.mockResolvedValue(undefined);
    mocks.recordBillingOperationEvent.mockResolvedValue(undefined);
    mocks.customerCreate.mockResolvedValue({ id: "cus_123" });
    mocks.upsertBillingCustomer.mockResolvedValue(undefined);
    mocks.checkoutCreate.mockResolvedValue({
      id: "cs_123",
      url: "https://stripe.test/checkout",
      expires_at: 1777595400,
    });
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
      { idempotencyKey: "billing-checkout:account-1:plus:reservation-1" },
    );
    expect(mocks.customerCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        email: "owner@example.com",
      }),
      { idempotencyKey: "billing-customer:account-1" },
    );
    expect(mocks.completeCheckoutSessionReservation).toHaveBeenCalledWith(
      expect.anything(),
      "reservation-1",
      expect.objectContaining({ id: "cs_123" }),
    );
  });

  it("returns an existing open checkout session without creating another Stripe session", async () => {
    mocks.findReusableCheckoutSession.mockResolvedValue({
      id: "reservation-existing",
      stripe_checkout_url: "https://stripe.test/existing",
    });
    const req = new Request("http://localhost:3002/api/billing/checkout", {
      method: "POST",
      body: JSON.stringify({ plan_key: "plus" }),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toMatchObject({
      status: "success",
      url: "https://stripe.test/existing",
      reused: true,
    });
    expect(mocks.customerCreate).not.toHaveBeenCalled();
    expect(mocks.checkoutCreate).not.toHaveBeenCalled();
  });

  it("logs checkout failures and returns a sanitized error", async () => {
    mocks.checkoutCreate.mockRejectedValue(new Error("Neither STRIPE_SECRET_KEY nor STRIPE_RESTRICTED_KEY is configured"));
    const req = new Request("http://localhost:3002/api/billing/checkout", {
      method: "POST",
      body: JSON.stringify({ plan_key: "plus" }),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(500);
    expect(body).toMatchObject({
      status: "unavailable",
      code: "billing_checkout_unavailable",
      message: "Billing checkout could not start. Please try again or contact support.",
    });
    expect(body.message).not.toContain("STRIPE_SECRET_KEY");
    expect(mocks.recordBillingOperationEvent).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        severity: "error",
        event_type: "checkout_failed",
        source: "checkout",
        internal_message: "Neither STRIPE_SECRET_KEY nor STRIPE_RESTRICTED_KEY is configured",
      }),
    );
  });
});
