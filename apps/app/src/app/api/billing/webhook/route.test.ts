import { beforeEach, describe, expect, it, vi } from "vitest";
import type Stripe from "stripe";

const mocks = vi.hoisted(() => ({
  createAdminClient: vi.fn(),
  constructEvent: vi.fn(),
  subscriptionRetrieve: vi.fn(),
  beginBillingWebhookEvent: vi.fn(),
  finishBillingWebhookEvent: vi.fn(),
  upsertBillingCustomer: vi.fn(),
  syncStripeSubscription: vi.fn(),
  downgradeSubscriptionToFree: vi.fn(),
  markCheckoutSessionStatus: vi.fn(),
  recordBillingOperationEvent: vi.fn(),
}));

vi.mock("@/lib/supabase/admin", () => ({
  createAdminClient: mocks.createAdminClient,
}));

vi.mock("@/lib/billing/stripe", () => ({
  getStripeClient: () => ({
    webhooks: { constructEvent: mocks.constructEvent },
    subscriptions: { retrieve: mocks.subscriptionRetrieve },
  }),
}));

vi.mock("@/lib/billing/webhook-events", () => ({
  beginBillingWebhookEvent: mocks.beginBillingWebhookEvent,
  finishBillingWebhookEvent: mocks.finishBillingWebhookEvent,
}));

vi.mock("@/lib/billing/sync-subscription", () => ({
  upsertBillingCustomer: mocks.upsertBillingCustomer,
  syncStripeSubscription: mocks.syncStripeSubscription,
  downgradeSubscriptionToFree: mocks.downgradeSubscriptionToFree,
}));

vi.mock("@/lib/billing/checkout-session", () => ({
  markCheckoutSessionStatus: mocks.markCheckoutSessionStatus,
}));

vi.mock("@/lib/billing/ops-log", () => ({
  errorToInternalMessage: (error: unknown) =>
    error instanceof Error ? error.message : String(error),
  recordBillingOperationEvent: mocks.recordBillingOperationEvent,
}));

import { POST } from "./route";

function stripeEvent(
  overrides: Partial<Stripe.Event> & { type: string; data: { object: unknown } },
): Stripe.Event {
  return {
    id: "evt_123",
    object: "event",
    api_version: "2026-02-25.clover",
    created: 1777593600,
    livemode: false,
    pending_webhooks: 1,
    request: null,
    ...overrides,
  } as Stripe.Event;
}

function subscription(overrides: Partial<Stripe.Subscription> = {}): Stripe.Subscription {
  return {
    id: "sub_123",
    object: "subscription",
    status: "active",
    customer: "cus_123",
    metadata: { account_id: "account-1" },
    cancel_at_period_end: false,
    items: { data: [{ price: { id: "price_plus" } }] },
    ...overrides,
  } as unknown as Stripe.Subscription;
}

describe("POST /api/billing/webhook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.STRIPE_WEBHOOK_SECRET = "whsec_test";
    mocks.createAdminClient.mockReturnValue({});
    mocks.beginBillingWebhookEvent.mockResolvedValue({
      action: "process",
      record: {
        stripe_event_id: "evt_123",
        event_type: "customer.subscription.updated",
        stripe_created_at: "2026-05-01T00:00:00.000Z",
        processing_status: "processing",
        attempt_count: 1,
      },
    });
    mocks.finishBillingWebhookEvent.mockResolvedValue(undefined);
    mocks.subscriptionRetrieve.mockResolvedValue(subscription());
    mocks.syncStripeSubscription.mockResolvedValue({ applied: true });
    mocks.downgradeSubscriptionToFree.mockResolvedValue({ applied: true });
    mocks.upsertBillingCustomer.mockResolvedValue(undefined);
    mocks.markCheckoutSessionStatus.mockResolvedValue(undefined);
    mocks.recordBillingOperationEvent.mockResolvedValue(undefined);
  });

  it("returns success without reprocessing duplicate webhook events", async () => {
    mocks.constructEvent.mockReturnValue(
      stripeEvent({
        type: "customer.subscription.updated",
        data: { object: subscription() },
      }),
    );
    mocks.beginBillingWebhookEvent.mockResolvedValueOnce({
      action: "skip",
      record: {
        stripe_event_id: "evt_123",
        event_type: "customer.subscription.updated",
        stripe_created_at: "2026-05-01T00:00:00.000Z",
        processing_status: "processed",
        attempt_count: 1,
      },
    });

    const res = await POST(new Request("http://localhost/api/billing/webhook", {
      method: "POST",
      headers: { "stripe-signature": "sig" },
      body: "{}",
    }) as never);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toMatchObject({ received: true, duplicate: true });
    expect(mocks.syncStripeSubscription).not.toHaveBeenCalled();
    expect(mocks.finishBillingWebhookEvent).not.toHaveBeenCalled();
  });

  it("logs and ignores stale subscription updates", async () => {
    mocks.constructEvent.mockReturnValue(
      stripeEvent({
        id: "evt_old",
        type: "customer.subscription.updated",
        data: { object: subscription() },
      }),
    );
    mocks.syncStripeSubscription.mockResolvedValueOnce({
      applied: false,
      reason: "stale_event",
      last_stripe_event_created_at: "2026-05-02T00:00:00.000Z",
    });

    const res = await POST(new Request("http://localhost/api/billing/webhook", {
      method: "POST",
      headers: { "stripe-signature": "sig" },
      body: "{}",
    }) as never);

    expect(res.status).toBe(200);
    expect(mocks.finishBillingWebhookEvent).toHaveBeenCalledWith(
      expect.anything(),
      "evt_old",
      { status: "ignored" },
    );
    expect(mocks.recordBillingOperationEvent).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        severity: "warning",
        event_type: "webhook_stale_subscription_event",
        stripe_event_id: "evt_old",
      }),
    );
  });

  it("marks webhook failures retryable and records an admin issue", async () => {
    mocks.constructEvent.mockReturnValue(
      stripeEvent({
        id: "evt_fail",
        type: "customer.subscription.updated",
        data: { object: subscription() },
      }),
    );
    mocks.syncStripeSubscription.mockRejectedValueOnce(new Error("database unavailable"));

    const res = await POST(new Request("http://localhost/api/billing/webhook", {
      method: "POST",
      headers: { "stripe-signature": "sig" },
      body: "{}",
    }) as never);
    const body = await res.json();

    expect(res.status).toBe(500);
    expect(body).toMatchObject({
      code: "billing_webhook_processing_failed",
      message: "Webhook handling failed.",
    });
    expect(mocks.finishBillingWebhookEvent).toHaveBeenCalledWith(
      expect.anything(),
      "evt_fail",
      { status: "failed", error: "database unavailable" },
    );
    expect(mocks.recordBillingOperationEvent).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        severity: "error",
        event_type: "webhook_processing_failed",
        internal_message: "database unavailable",
      }),
    );
  });
});
