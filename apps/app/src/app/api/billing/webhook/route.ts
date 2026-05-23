import { NextRequest, NextResponse } from "next/server";
import Stripe from "stripe";
import { markCheckoutSessionStatus } from "@/lib/billing/checkout-session";
import { errorToInternalMessage, recordBillingOperationEvent } from "@/lib/billing/ops-log";
import {
  beginBillingWebhookEvent,
  finishBillingWebhookEvent,
} from "@/lib/billing/webhook-events";
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
  } catch {
    return NextResponse.json(
      {
        status: "signature_error",
        message: "Invalid webhook signature.",
      },
      { status: 400 },
    );
  }

  const stripeEventCreatedAt = new Date(event.created * 1000).toISOString();
  let supabase: ReturnType<typeof createAdminClient> | null = null;
  try {
    supabase = createAdminClient();
    const stripe = getStripeClient();
    const ledger = await beginBillingWebhookEvent(supabase, {
      stripe_event_id: event.id,
      event_type: event.type,
      stripe_created_at: stripeEventCreatedAt,
    });

    if (ledger.action === "skip") {
      return NextResponse.json({ received: true, duplicate: true });
    }

    let ignoredAsStale = false;
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
          const syncResult = await syncStripeSubscription(supabase, subscription, {
            stripe_event_id: event.id,
            stripe_event_created_at: stripeEventCreatedAt,
          });
          ignoredAsStale = !syncResult.applied;
          if (!syncResult.applied) {
            await recordStaleSubscriptionEvent(supabase, event, {
              account_id: subscription.metadata.account_id,
              stripe_customer_id: customerId ?? null,
              stripe_subscription_id: subscription.id,
              last_stripe_event_created_at: syncResult.last_stripe_event_created_at,
            });
          }
        }
        await markCheckoutSessionStatus(supabase, {
          stripe_checkout_session_id: session.id,
          account_id: accountId,
          status: "completed",
        });
        break;
      }
      case "customer.subscription.created":
      case "customer.subscription.updated": {
        const eventSubscription = event.data.object as Stripe.Subscription;
        const subscription = await stripe.subscriptions.retrieve(eventSubscription.id);
        const syncResult = await syncStripeSubscription(supabase, subscription, {
          stripe_event_id: event.id,
          stripe_event_created_at: stripeEventCreatedAt,
        });
        ignoredAsStale = !syncResult.applied;
        if (!syncResult.applied) {
          await recordStaleSubscriptionEvent(supabase, event, {
            account_id: subscription.metadata.account_id,
            stripe_customer_id: subscription.customer,
            stripe_subscription_id: subscription.id,
            last_stripe_event_created_at: syncResult.last_stripe_event_created_at,
          });
        }
        break;
      }
      case "customer.subscription.deleted": {
        const subscription = event.data.object as Stripe.Subscription;
        const syncResult = await downgradeSubscriptionToFree(supabase, subscription, {
          stripe_event_id: event.id,
          stripe_event_created_at: stripeEventCreatedAt,
        });
        ignoredAsStale = !syncResult.applied;
        if (!syncResult.applied) {
          await recordStaleSubscriptionEvent(supabase, event, {
            account_id: subscription.metadata.account_id,
            stripe_customer_id: subscription.customer,
            stripe_subscription_id: subscription.id,
            last_stripe_event_created_at: syncResult.last_stripe_event_created_at,
          });
        }
        break;
      }
      case "checkout.session.expired": {
        const session = event.data.object as Stripe.Checkout.Session;
        await markCheckoutSessionStatus(supabase, {
          stripe_checkout_session_id: session.id,
          account_id: session.metadata?.account_id,
          status: "expired",
        });
        break;
      }
      default:
        break;
    }

    await finishBillingWebhookEvent(supabase, event.id, {
      status: ignoredAsStale ? "ignored" : "processed",
    });
    return NextResponse.json({ received: true });
  } catch (error) {
    console.error("[billing/webhook] failed", error);
    if (supabase) {
      await finishBillingWebhookEvent(supabase, event.id, {
        status: "failed",
        error: errorToInternalMessage(error),
      }).catch((finishError) => {
        console.warn("[billing/webhook] failed to mark webhook event failed", finishError);
      });
      await recordBillingOperationEvent(supabase, {
        severity: "error",
        event_type: "webhook_processing_failed",
        source: "webhook",
        public_message: "Stripe webhook processing failed.",
        internal_message: errorToInternalMessage(error),
        stripe_event_id: event.id,
        metadata: {
          stripe_event_type: event.type,
          stripe_event_created_at: stripeEventCreatedAt,
        },
      });
    }
    return NextResponse.json(
      {
        status: "webhook_error",
        code: "billing_webhook_processing_failed",
        message: "Webhook handling failed.",
      },
      { status: 500 },
    );
  }
}

async function recordStaleSubscriptionEvent(
  supabase: ReturnType<typeof createAdminClient>,
  event: Stripe.Event,
  params: {
    account_id?: string | null;
    stripe_customer_id?: string | Stripe.Customer | Stripe.DeletedCustomer | null;
    stripe_subscription_id?: string | null;
    last_stripe_event_created_at?: string | null;
  },
) {
  const customerId =
    typeof params.stripe_customer_id === "string"
      ? params.stripe_customer_id
      : params.stripe_customer_id?.id;
  await recordBillingOperationEvent(supabase, {
    severity: "warning",
    event_type: "webhook_stale_subscription_event",
    source: "webhook",
    public_message: "A stale Stripe subscription event was ignored.",
    internal_message: `Ignored ${event.type} because a newer Stripe event was already applied.`,
    account_id: params.account_id,
    stripe_customer_id: customerId ?? null,
    stripe_subscription_id: params.stripe_subscription_id,
    stripe_event_id: event.id,
    metadata: {
      stripe_event_type: event.type,
      stripe_event_created_at: new Date(event.created * 1000).toISOString(),
      last_stripe_event_created_at: params.last_stripe_event_created_at ?? null,
    },
  });
}
