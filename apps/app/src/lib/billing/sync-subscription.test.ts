import { beforeEach, describe, expect, it } from "vitest";
import type Stripe from "stripe";
import { downgradeSubscriptionToFree, syncStripeSubscription } from "./sync-subscription";

class FakeTable {
  constructor(
    private readonly sink: unknown[],
    private readonly existingSubscription: { last_stripe_event_created_at: string | null } | null,
  ) {}

  select() {
    return this;
  }

  eq() {
    return this;
  }

  maybeSingle() {
    return { data: this.existingSubscription, error: null };
  }

  upsert(payload: unknown) {
    this.sink.push(payload);
    return { error: null };
  }
}

class FakeSupabase {
  public rows: unknown[] = [];
  public existingSubscription: { last_stripe_event_created_at: string | null } | null = null;

  from() {
    return new FakeTable(this.rows, this.existingSubscription);
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
    await syncStripeSubscription(supabase as never, subscription(), {
      stripe_event_id: "evt_1",
      stripe_event_created_at: "2026-05-01T00:00:00.000Z",
    });
    expect(supabase.rows[0]).toMatchObject({
      account_id: "33333333-3333-3333-3333-333333333333",
      plan_key: "plus",
      status: "active",
      stripe_subscription_id: "sub_123",
      stripe_price_id: "price_plus",
      last_stripe_event_id: "evt_1",
      last_stripe_event_created_at: "2026-05-01T00:00:00.000Z",
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

  it("skips stale subscription events without mutating the row", async () => {
    const supabase = new FakeSupabase();
    supabase.existingSubscription = {
      last_stripe_event_created_at: "2026-05-02T00:00:00.000Z",
    };
    const result = await syncStripeSubscription(supabase as never, subscription(), {
      stripe_event_id: "evt_old",
      stripe_event_created_at: "2026-05-01T00:00:00.000Z",
    });

    expect(result).toMatchObject({
      applied: false,
      reason: "stale_event",
      last_stripe_event_created_at: "2026-05-02T00:00:00.000Z",
    });
    expect(supabase.rows).toHaveLength(0);
  });
});
