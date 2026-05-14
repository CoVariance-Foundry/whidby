import { NextRequest, NextResponse } from "next/server";
import Stripe from "stripe";
import {
  downgradeSubscriptionToFree,
  syncStripeSubscription,
  upsertBillingCustomer,
} from "@/lib/billing/sync-subscription";
import { getStripeClient } from "@/lib/billing/stripe";
import { createAdminClient } from "@/lib/supabase/admin";

export async function POST(req: NextRequest) {
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!webhookSecret) {
    return NextResponse.json(
      { status: "configuration_error", message: "STRIPE_WEBHOOK_SECRET is not configured." },
      { status: 500 },
    );
  }

  const signature = req.headers.get("stripe-signature");
  if (!signature) {
    return NextResponse.json(
      { status: "validation_error", message: "Missing Stripe signature." },
      { status: 400 },
    );
  }

  let event: Stripe.Event;
  const payload = await req.text();
  try {
    event = getStripeClient().webhooks.constructEvent(
      payload,
      signature,
      webhookSecret,
    );
  } catch (error) {
    return NextResponse.json(
      {
        status: "signature_error",
        message: error instanceof Error ? error.message : "Invalid webhook signature.",
      },
      { status: 400 },
    );
  }

  try {
    const supabase = createAdminClient();
    const stripe = getStripeClient();

    switch (event.type) {
      case "checkout.session.completed": {
        const session = event.data.object as Stripe.Checkout.Session;
        const accountId = session.metadata?.account_id;
        const userId = session.metadata?.user_id ?? null;
        const customerId =
          typeof session.customer === "string" ? session.customer : session.customer?.id;
        if (accountId && customerId) {
          await upsertBillingCustomer(supabase, {
            account_id: accountId,
            user_id: userId,
            stripe_customer_id: customerId,
          });
        }
        if (typeof session.subscription === "string") {
          const subscription = await stripe.subscriptions.retrieve(session.subscription);
          await syncStripeSubscription(supabase, subscription);
        }
        break;
      }
      case "customer.subscription.created":
      case "customer.subscription.updated": {
        await syncStripeSubscription(
          supabase,
          event.data.object as Stripe.Subscription,
        );
        break;
      }
      case "customer.subscription.deleted": {
        await downgradeSubscriptionToFree(
          supabase,
          event.data.object as Stripe.Subscription,
        );
        break;
      }
      default:
        break;
    }

    return NextResponse.json({ received: true });
  } catch (error) {
    console.error("[billing/webhook] failed", error);
    return NextResponse.json(
      {
        status: "webhook_error",
        message: error instanceof Error ? error.message : "Webhook handling failed.",
      },
      { status: 500 },
    );
  }
}
