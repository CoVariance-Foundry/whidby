import type Stripe from "stripe";
import type { SupabaseClient } from "@supabase/supabase-js";
import type { PaidPlanKey } from "./stripe";

export type BillingCheckoutSession = {
  id: string;
  account_id: string;
  user_id: string | null;
  plan_key: PaidPlanKey;
  status: "pending" | "completed" | "cancelled" | "expired";
  stripe_checkout_session_id: string | null;
  stripe_checkout_url: string | null;
  expires_at: string;
  idempotency_key: string;
};

const CHECKOUT_SESSION_TTL_MS = 30 * 60 * 1000;

export async function findReusableCheckoutSession(
  supabase: SupabaseClient,
  accountId: string,
  planKey: PaidPlanKey,
  now = new Date(),
): Promise<BillingCheckoutSession | null> {
  const { data, error } = await supabase
    .from("billing_checkout_sessions")
    .select(
      "id, account_id, user_id, plan_key, status, stripe_checkout_session_id, stripe_checkout_url, expires_at, idempotency_key",
    )
    .eq("account_id", accountId)
    .eq("plan_key", planKey)
    .eq("status", "pending")
    .gt("expires_at", now.toISOString())
    .not("stripe_checkout_url", "is", null)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (error) throw new Error(`checkout session lookup failed: ${error.message}`);
  return (data as BillingCheckoutSession | null) ?? null;
}

export async function expireStaleOrCompetingCheckoutSessions(
  supabase: SupabaseClient,
  accountId: string,
  planKey: PaidPlanKey,
  now = new Date(),
): Promise<void> {
  const update = {
    status: "expired",
    updated_at: now.toISOString(),
  };

  const stale = await supabase
    .from("billing_checkout_sessions")
    .update(update)
    .eq("account_id", accountId)
    .eq("status", "pending")
    .lte("expires_at", now.toISOString());
  if (stale.error) throw new Error(`checkout session expiry failed: ${stale.error.message}`);

  const competing = await supabase
    .from("billing_checkout_sessions")
    .update(update)
    .eq("account_id", accountId)
    .eq("status", "pending")
    .neq("plan_key", planKey);
  if (competing.error) {
    throw new Error(`checkout session replacement failed: ${competing.error.message}`);
  }
}

export async function reserveCheckoutSession(
  supabase: SupabaseClient,
  params: {
    account_id: string;
    user_id: string;
    plan_key: PaidPlanKey;
    now?: Date;
  },
): Promise<BillingCheckoutSession> {
  const now = params.now ?? new Date();
  const reservationId = crypto.randomUUID();
  const expiresAt = new Date(now.getTime() + CHECKOUT_SESSION_TTL_MS).toISOString();
  const idempotencyKey = `billing-checkout:${params.account_id}:${params.plan_key}:${reservationId}`;

  const { data, error } = await supabase
    .from("billing_checkout_sessions")
    .insert({
      id: reservationId,
      account_id: params.account_id,
      user_id: params.user_id,
      plan_key: params.plan_key,
      status: "pending",
      expires_at: expiresAt,
      idempotency_key: idempotencyKey,
      updated_at: now.toISOString(),
    })
    .select(
      "id, account_id, user_id, plan_key, status, stripe_checkout_session_id, stripe_checkout_url, expires_at, idempotency_key",
    )
    .single();

  if (error) throw new Error(`checkout session reservation failed: ${error.message}`);
  return data as BillingCheckoutSession;
}

export async function completeCheckoutSessionReservation(
  supabase: SupabaseClient,
  reservationId: string,
  session: Stripe.Checkout.Session,
): Promise<void> {
  if (!session.url) {
    throw new Error(`Stripe checkout session ${session.id} did not include a URL`);
  }

  const expiresAt =
    typeof session.expires_at === "number"
      ? new Date(session.expires_at * 1000).toISOString()
      : undefined;
  const { error } = await supabase
    .from("billing_checkout_sessions")
    .update({
      stripe_checkout_session_id: session.id,
      stripe_checkout_url: session.url,
      ...(expiresAt ? { expires_at: expiresAt } : {}),
      updated_at: new Date().toISOString(),
    })
    .eq("id", reservationId);

  if (error) throw new Error(`checkout session completion failed: ${error.message}`);
}

export async function markCheckoutSessionStatus(
  supabase: SupabaseClient,
  params: {
    stripe_checkout_session_id?: string | null;
    account_id?: string | null;
    status: "completed" | "cancelled" | "expired";
  },
): Promise<void> {
  let query = supabase
    .from("billing_checkout_sessions")
    .update({ status: params.status, updated_at: new Date().toISOString() });

  if (params.stripe_checkout_session_id) {
    query = query.eq("stripe_checkout_session_id", params.stripe_checkout_session_id);
  } else if (params.account_id) {
    query = query.eq("account_id", params.account_id).eq("status", "pending");
  } else {
    return;
  }

  const { error } = await query;
  if (error) throw new Error(`checkout session status update failed: ${error.message}`);
}
