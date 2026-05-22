import { NextRequest, NextResponse } from "next/server";
import { resolveEntitlementContext } from "@/lib/account/entitlements";
import { PRODUCT_FLAGS } from "@/lib/flags/product-flags";
import { getServerFeatureFlag } from "@/lib/flags/server";
import {
  completeCheckoutSessionReservation,
  expireStaleOrCompetingCheckoutSessions,
  findReusableCheckoutSession,
  reserveCheckoutSession,
} from "@/lib/billing/checkout-session";
import { errorToInternalMessage, recordBillingOperationEvent } from "@/lib/billing/ops-log";
import { getPriceIdForPlan, getStripeClient, isPaidPlan } from "@/lib/billing/stripe";
import { upsertBillingCustomer } from "@/lib/billing/sync-subscription";
import { getRequestOrigin } from "@/lib/api/upstream";
import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";

const CHECKOUT_PUBLIC_ERROR =
  "Billing checkout could not start. Please try again or contact support.";

export async function POST(req: NextRequest) {
  let admin: ReturnType<typeof createAdminClient> | null = null;
  let logContext: {
    account_id?: string | null;
    user_id?: string | null;
    plan_key?: string | null;
    stripe_customer_id?: string | null;
    stripe_checkout_session_id?: string | null;
  } = {};

  try {
    const supabase = await createClient();
    const { user, entitlement } = await resolveEntitlementContext(supabase);
    logContext = {
      account_id: entitlement.account_id,
      user_id: user.id,
      plan_key: entitlement.plan_key,
    };
    const enabled = await getServerFeatureFlag(
      PRODUCT_FLAGS.billingCheckoutEnabled.key,
      PRODUCT_FLAGS.billingCheckoutEnabled.defaultValue,
      user.id,
      {
        account_id: entitlement.account_id,
        tier: entitlement.plan_key,
      },
    );

    if (!enabled) {
      return NextResponse.json(
        {
          status: "disabled",
          code: "billing_checkout_disabled",
          message: "Billing checkout is not available yet.",
        },
        { status: 503 },
      );
    }

    const body = await req.json();
    if (!isPaidPlan(body?.plan_key)) {
      return NextResponse.json(
        { status: "validation_error", message: "plan_key must be plus or pro." },
        { status: 400 },
      );
    }
    logContext.plan_key = body.plan_key;

    admin = createAdminClient();
    const stripe = getStripeClient();
    const origin = process.env.NEXT_PUBLIC_APP_FRONTEND_URL ?? getRequestOrigin(req);
    const priceId = getPriceIdForPlan(body.plan_key);
    const reusable = await findReusableCheckoutSession(
      admin,
      entitlement.account_id,
      body.plan_key,
    );

    if (reusable?.stripe_checkout_url) {
      return NextResponse.json({
        status: "success",
        url: reusable.stripe_checkout_url,
        reused: true,
      });
    }

    await expireStaleOrCompetingCheckoutSessions(
      admin,
      entitlement.account_id,
      body.plan_key,
    );

    const { data: existingCustomer, error: customerReadError } = await admin
      .from("billing_customers")
      .select("stripe_customer_id")
      .eq("account_id", entitlement.account_id)
      .maybeSingle();

    if (customerReadError) {
      throw new Error(customerReadError.message);
    }

    const { data: activeSubscription, error: subscriptionReadError } = await admin
      .from("subscriptions")
      .select("status, stripe_subscription_id, plan_key")
      .eq("account_id", entitlement.account_id)
      .in("status", ["active", "trialing", "past_due"])
      .maybeSingle();

    if (subscriptionReadError) {
      throw new Error(subscriptionReadError.message);
    }

    if (activeSubscription?.stripe_subscription_id) {
      return NextResponse.json(
        {
          status: "conflict",
          code: "active_subscription_exists",
          message: "This account already has an active subscription.",
        },
        { status: 409 },
      );
    }

    let customerId = existingCustomer?.stripe_customer_id as string | undefined;
    if (!customerId) {
      const customer = await stripe.customers.create(
        {
          email: user.email ?? undefined,
          metadata: {
            account_id: entitlement.account_id,
            user_id: user.id,
          },
        },
        { idempotencyKey: `billing-customer:${entitlement.account_id}` },
      );
      customerId = customer.id;
      await upsertBillingCustomer(admin, {
        account_id: entitlement.account_id,
        user_id: user.id,
        stripe_customer_id: customerId,
      });
    }
    logContext.stripe_customer_id = customerId;

    const reservation = await reserveCheckoutSession(admin, {
      account_id: entitlement.account_id,
      user_id: user.id,
      plan_key: body.plan_key,
    });

    const session = await stripe.checkout.sessions.create(
      {
        mode: "subscription",
        customer: customerId,
        line_items: [{ price: priceId, quantity: 1 }],
        success_url: `${origin}/settings?billing=success`,
        cancel_url: `${origin}/settings?billing=cancelled`,
        metadata: {
          account_id: entitlement.account_id,
          user_id: user.id,
          plan_key: body.plan_key,
        },
        subscription_data: {
          metadata: {
            account_id: entitlement.account_id,
            user_id: user.id,
            plan_key: body.plan_key,
          },
        },
      },
      { idempotencyKey: reservation.idempotency_key },
    );
    logContext.stripe_checkout_session_id = session.id;
    await completeCheckoutSessionReservation(admin, reservation.id, session);

    return NextResponse.json({ status: "success", url: session.url });
  } catch (error) {
    console.error("[billing/checkout] failed", error);
    if (admin) {
      await recordBillingOperationEvent(admin, {
        severity: "error",
        event_type: "checkout_failed",
        source: "checkout",
        public_message: CHECKOUT_PUBLIC_ERROR,
        internal_message: errorToInternalMessage(error),
        account_id: logContext.account_id,
        user_id: logContext.user_id,
        stripe_customer_id: logContext.stripe_customer_id,
        stripe_checkout_session_id: logContext.stripe_checkout_session_id,
        metadata: { plan_key: logContext.plan_key },
      });
    }
    return NextResponse.json(
      {
        status: "unavailable",
        code: "billing_checkout_unavailable",
        message: CHECKOUT_PUBLIC_ERROR,
      },
      { status: 500 },
    );
  }
}
