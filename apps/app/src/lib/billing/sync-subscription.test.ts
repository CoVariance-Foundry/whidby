import { beforeEach, describe, expect, it } from "vitest";
import type Stripe from "stripe";
import { downgradeSubscriptionToFree, syncStripeSubscription } from "./sync-subscription";

class FakeTable {
  constructor(private readonly sink: unknown[]) {}

  upsert(payload: unknown) {
    this.sink.push(payload);
    return { error: null };
  }
}

class FakeSupabase {
  public rows: unknown[] = [];

  from() {
    return new FakeTable(this.rows);
  }
}

function subscription(overrides: Partial<Stripe.Subscription> = {}): Stripe.Subscription {
  return {
    id: "sub_123",
    status: "active",
    metadata: { account_id: "33333333-3333-3333-3333-333333333333" },
    cancel_at_period_end: false,
    items: {
      data: [{
        price: { id: "price_plus" },
        current_period_start: 1777593600,
        current_period_end: 1780272000,
      }],
    },
    ...overrides,
  } as unknown as Stripe.Subscription;
}

describe("Stripe subscription sync", () => {
  beforeEach(() => {
    process.env.STRIPE_PLUS_PRICE_ID = "price_plus";
    process.env.STRIPE_PRO_PRICE_ID = "price_pro";
  });

  it("syncs a Stripe subscription into the account subscription row", async () => {
    const supabase = new FakeSupabase();
    await syncStripeSubscription(supabase as never, subscription());
    expect(supabase.rows[0]).toMatchObject({
      account_id: "33333333-3333-3333-3333-333333333333",
      plan_key: "plus",
      status: "active",
      stripe_subscription_id: "sub_123",
      stripe_price_id: "price_plus",
    });
  });

  it("fails sync when Stripe sends an unknown price id", async () => {
    const supabase = new FakeSupabase();
    await expect(
      syncStripeSubscription(
        supabase as never,
        subscription({
          items: {
            data: [{
              price: { id: "price_unknown" },
              current_period_start: 1777593600,
              current_period_end: 1780272000,
            }],
          } as Stripe.ApiList<Stripe.SubscriptionItem>,
        }),
      ),
    ).rejects.toThrow("Unknown Stripe price id: price_unknown");
    expect(supabase.rows).toHaveLength(0);
  });

  it("downgrades deleted subscriptions to free", async () => {
    const supabase = new FakeSupabase();
    await downgradeSubscriptionToFree(
      supabase as never,
      subscription({ status: "canceled" }),
    );
    expect(supabase.rows[0]).toMatchObject({
      plan_key: "free",
      status: "canceled",
      stripe_price_id: null,
    });
  });
});
