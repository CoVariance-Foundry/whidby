import { NextRequest, NextResponse } from "next/server";
import { resolveEntitlementContext } from "@/lib/account/entitlements";
import { PRODUCT_FLAGS } from "@/lib/flags/product-flags";
import { getServerFeatureFlag } from "@/lib/flags/server";
import { getStripeClient } from "@/lib/billing/stripe";
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
          message: "Billing management is not available yet.",
        },
        { status: 503 },
      );
    }

    const admin = createAdminClient();
    const { data, error } = await admin
      .from("billing_customers")
      .select("stripe_customer_id")
      .eq("account_id", entitlement.account_id)
      .maybeSingle();

    if (error) throw new Error(error.message);
    if (!data?.stripe_customer_id) {
      return NextResponse.json(
        {
          status: "not_found",
          code: "billing_customer_missing",
          message: "No billing customer exists for this account.",
        },
        { status: 404 },
      );
    }

    const origin = process.env.NEXT_PUBLIC_APP_FRONTEND_URL ?? req.nextUrl.origin;
    const session = await getStripeClient().billingPortal.sessions.create({
      customer: data.stripe_customer_id,
      return_url: `${origin}/reports`,
    });

    return NextResponse.json({ status: "success", url: session.url });
  } catch (error) {
    console.error("[billing/portal] failed", error);
    return NextResponse.json(
      {
        status: "unavailable",
        message: error instanceof Error ? error.message : "Failed to open billing portal.",
      },
      { status: 500 },
    );
  }
}
