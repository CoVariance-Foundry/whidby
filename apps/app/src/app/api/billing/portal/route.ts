import { NextRequest, NextResponse } from "next/server";
import { resolveEntitlementContext } from "@/lib/account/entitlements";
import { PRODUCT_FLAGS } from "@/lib/flags/product-flags";
import { getServerFeatureFlag } from "@/lib/flags/server";
import { errorToInternalMessage, recordBillingOperationEvent } from "@/lib/billing/ops-log";
import { getStripeClient } from "@/lib/billing/stripe";
import { getRequestOrigin } from "@/lib/api/upstream";
import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";

const PORTAL_PUBLIC_ERROR =
  "Billing management could not open. Please try again or contact support.";

export async function POST(req: NextRequest) {
  let admin: ReturnType<typeof createAdminClient> | null = null;
  let logContext: {
    account_id?: string | null;
    user_id?: string | null;
    stripe_customer_id?: string | null;
  } = {};

  try {
    const supabase = await createClient();
    const { user, entitlement } = await resolveEntitlementContext(supabase);
    logContext = { account_id: entitlement.account_id, user_id: user.id };
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
          message: "Billing management is not available yet.",
        },
        { status: 503 },
      );
    }

    admin = createAdminClient();
    const { data, error } = await admin
      .from("billing_customers")
      .select("stripe_customer_id")
      .eq("account_id", entitlement.account_id)
      .maybeSingle();

    if (error) throw new Error(error.message);
    if (!data?.stripe_customer_id) {
      await recordBillingOperationEvent(admin, {
        severity: "warning",
        event_type: "portal_customer_missing",
        source: "portal",
        public_message: "No billing customer exists for this account.",
        internal_message: "Billing portal requested before a Stripe customer was stored.",
        account_id: entitlement.account_id,
        user_id: user.id,
      });
      return NextResponse.json(
        {
          status: "not_found",
          code: "billing_customer_missing",
          message: "No billing customer exists for this account.",
        },
        { status: 404 },
      );
    }
    logContext.stripe_customer_id = data.stripe_customer_id;

    const origin = process.env.NEXT_PUBLIC_APP_FRONTEND_URL ?? getRequestOrigin(req);
    const session = await getStripeClient().billingPortal.sessions.create({
      customer: data.stripe_customer_id,
      return_url: `${origin}/settings?billing=success`,
    });

    return NextResponse.json({ status: "success", url: session.url });
  } catch (error) {
    console.error("[billing/portal] failed", error);
    if (admin) {
      await recordBillingOperationEvent(admin, {
        severity: "error",
        event_type: "portal_failed",
        source: "portal",
        public_message: PORTAL_PUBLIC_ERROR,
        internal_message: errorToInternalMessage(error),
        account_id: logContext.account_id,
        user_id: logContext.user_id,
        stripe_customer_id: logContext.stripe_customer_id,
      });
    }
    return NextResponse.json(
      {
        status: "unavailable",
        code: "billing_portal_unavailable",
        message: PORTAL_PUBLIC_ERROR,
      },
      { status: 500 },
    );
  }
}
