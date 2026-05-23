import type Stripe from "stripe";
import type { SupabaseClient } from "@supabase/supabase-js";
import { getPlanForPriceId } from "./stripe";

export type StripeEventContext = {
  stripe_event_id: string;
  stripe_event_created_at: string;
};

export type SubscriptionSyncResult =
  | { applied: true }
  | {
      applied: false;
      reason: "stale_event";
      last_stripe_event_created_at: string | null;
    };

export async function upsertBillingCustomer(
  supabase: SupabaseClient,
  params: {
    account_id: string;
    user_id: string | null;
    stripe_customer_id: string;
  },
) {
  const { error } = await supabase.from("billing_customers").upsert(
    {
      account_id: params.account_id,
      user_id: params.user_id,
      stripe_customer_id: params.stripe_customer_id,
      updated_at: new Date().toISOString(),
    },
    { onConflict: "account_id" },
  );
  if (error) throw new Error(`billing customer upsert failed: ${error.message}`);
}

export async function syncStripeSubscription(
  supabase: SupabaseClient,
  subscription: Stripe.Subscription,
  eventContext?: StripeEventContext,
): Promise<SubscriptionSyncResult> {
  const accountId = subscription.metadata.account_id;
  if (!accountId) {
    throw new Error(`subscription ${subscription.id} missing account_id metadata`);
  }

  const stale = await isStaleStripeEvent(supabase, accountId, eventContext);
  if (stale) return stale;

  const item = subscription.items.data[0];
  const planKey = getPlanForPriceId(item?.price.id);
  const currentPeriodStart = item?.current_period_start
    ? new Date(item.current_period_start * 1000).toISOString()
    : null;
  const currentPeriodEnd = item?.current_period_end
    ? new Date(item.current_period_end * 1000).toISOString()
    : null;

  const { error } = await supabase.from("subscriptions").upsert(
    {
      account_id: accountId,
      plan_key: planKey,
      status: subscription.status,
      stripe_subscription_id: subscription.id,
      stripe_price_id: item?.price.id ?? null,
      current_period_start: currentPeriodStart,
      current_period_end: currentPeriodEnd,
      cancel_at_period_end: subscription.cancel_at_period_end,
      last_stripe_event_id: eventContext?.stripe_event_id ?? null,
      last_stripe_event_created_at: eventContext?.stripe_event_created_at ?? null,
      updated_at: new Date().toISOString(),
    },
    { onConflict: "account_id" },
  );
  if (error) throw new Error(`subscription upsert failed: ${error.message}`);
  return { applied: true };
}

export async function downgradeSubscriptionToFree(
  supabase: SupabaseClient,
  subscription: Stripe.Subscription,
  eventContext?: StripeEventContext,
): Promise<SubscriptionSyncResult> {
  const accountId = subscription.metadata.account_id;
  if (!accountId) return { applied: true };

  const stale = await isStaleStripeEvent(supabase, accountId, eventContext);
  if (stale) return stale;

  const { error } = await supabase.from("subscriptions").upsert(
    {
      account_id: accountId,
      plan_key: "free",
      status: subscription.status,
      stripe_subscription_id: subscription.id,
      stripe_price_id: null,
      current_period_start: subscription.items.data[0]?.current_period_start
        ? new Date(subscription.items.data[0].current_period_start * 1000).toISOString()
        : null,
      current_period_end: subscription.items.data[0]?.current_period_end
        ? new Date(subscription.items.data[0].current_period_end * 1000).toISOString()
        : null,
      cancel_at_period_end: subscription.cancel_at_period_end,
      last_stripe_event_id: eventContext?.stripe_event_id ?? null,
      last_stripe_event_created_at: eventContext?.stripe_event_created_at ?? null,
      updated_at: new Date().toISOString(),
    },
    { onConflict: "account_id" },
  );
  if (error) throw new Error(`subscription downgrade failed: ${error.message}`);
  return { applied: true };
}

async function isStaleStripeEvent(
  supabase: SupabaseClient,
  accountId: string,
  eventContext?: StripeEventContext,
): Promise<Extract<SubscriptionSyncResult, { applied: false }> | null> {
  if (!eventContext?.stripe_event_created_at) return null;

  const { data, error } = await supabase
    .from("subscriptions")
    .select("last_stripe_event_created_at")
    .eq("account_id", accountId)
    .maybeSingle();
  if (error) throw new Error(`subscription event read failed: ${error.message}`);

  const lastCreatedAt =
    typeof data?.last_stripe_event_created_at === "string"
      ? data.last_stripe_event_created_at
      : null;
  if (lastCreatedAt && Date.parse(lastCreatedAt) >= Date.parse(eventContext.stripe_event_created_at)) {
    return {
      applied: false,
      reason: "stale_event",
      last_stripe_event_created_at: lastCreatedAt,
    };
  }

  return null;
}
