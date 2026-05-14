import { NextRequest, NextResponse } from "next/server";
import { resolveEntitlementContext } from "@/lib/account/entitlements";
import { PRODUCT_FLAGS } from "@/lib/flags/product-flags";
import { getServerFeatureFlag } from "@/lib/flags/server";
import { getPriceIdForPlan, getStripeClient, isPaidPlan } from "@/lib/billing/stripe";
import { upsertBillingCustomer } from "@/lib/billing/sync-subscription";
import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";

export async function POST(req: NextRequest) {
  try {
    const supabase = await createClient();
    const { user, entitlement } = await resolveEntitlementContext(supabase);
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

    const admin = createAdminClient();
    const stripe = getStripeClient();
    const origin = process.env.NEXT_PUBLIC_APP_FRONTEND_URL ?? req.nextUrl.origin;
    const priceId = getPriceIdForPlan(body.plan_key);

    const { data: existingCustomer, error: customerReadError } = await admin
      .from("billing_customers")
      .select("stripe_customer_id")
      .eq("account_id", entitlement.account_id)
      .maybeSingle();

    if (customerReadError) {
      throw new Error(customerReadError.message);
    }

    let customerId = existingCustomer?.stripe_customer_id as string | undefined;
    if (!customerId) {
      const customer = await stripe.customers.create({
        email: user.email ?? undefined,
        metadata: {
          account_id: entitlement.account_id,
          user_id: user.id,
        },
      });
      customerId = customer.id;
      await upsertBillingCustomer(admin, {
        account_id: entitlement.account_id,
        user_id: user.id,
        stripe_customer_id: customerId,
      });
    }

    const session = await stripe.checkout.sessions.create({
      mode: "subscription",
      customer: customerId,
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: `${origin}/reports?billing=success`,
      cancel_url: `${origin}/reports?billing=cancelled`,
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
    });

    return NextResponse.json({ status: "success", url: session.url });
  } catch (error) {
    console.error("[billing/checkout] failed", error);
    return NextResponse.json(
      {
        status: "unavailable",
        message: error instanceof Error ? error.message : "Failed to start checkout.",
      },
      { status: 500 },
    );
  }
}
