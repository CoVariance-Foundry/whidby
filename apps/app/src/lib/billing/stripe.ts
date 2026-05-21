import Stripe from "stripe";

let stripe: Stripe | null = null;

export type PaidPlanKey = "plus" | "pro";

export function getStripeClient(): Stripe {
  const key = process.env.STRIPE_SECRET_KEY ?? process.env.STRIPE_RESTRICTED_KEY;
  if (!key) {
    throw new Error("Neither STRIPE_SECRET_KEY nor STRIPE_RESTRICTED_KEY is configured");
  }

  if (!stripe) {
    stripe = new Stripe(key, {
      maxNetworkRetries: 2,
    });
  }

  return stripe;
}

export function getPriceIdForPlan(plan: PaidPlanKey): string {
  const envKey = plan === "plus" ? "STRIPE_PLUS_PRICE_ID" : "STRIPE_PRO_PRICE_ID";
  const priceId = process.env[envKey];
  if (!priceId) {
    throw new Error(`${envKey} is not configured`);
  }
  return priceId;
}

export function getPlanForPriceId(priceId: string | null | undefined): PaidPlanKey {
  if (priceId && priceId === process.env.STRIPE_PLUS_PRICE_ID) return "plus";
  if (priceId && priceId === process.env.STRIPE_PRO_PRICE_ID) return "pro";
  throw new Error(`Unknown Stripe price id: ${priceId ?? "missing"}`);
}

export function isPaidPlan(value: unknown): value is PaidPlanKey {
  return value === "plus" || value === "pro";
}
