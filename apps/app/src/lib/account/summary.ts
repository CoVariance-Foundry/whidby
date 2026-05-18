import type { SupabaseClient, User } from "@supabase/supabase-js";
import type { AccountEntitlement, PlanKey } from "@/lib/account/entitlements";
import { PRODUCT_FLAGS } from "@/lib/flags/product-flags";
import { getServerFeatureFlag } from "@/lib/flags/server";

const PLAN_DETAILS: Record<
  PlanKey,
  { label: string; monthly_price_cents: number; monthly_report_limit: number }
> = {
  free: { label: "Free", monthly_price_cents: 0, monthly_report_limit: 0 },
  plus: { label: "Plus", monthly_price_cents: 4900, monthly_report_limit: 10 },
  pro: { label: "Pro", monthly_price_cents: 10000, monthly_report_limit: 50 },
};

export interface AccountSummary {
  account_id: string;
  email: string;
  plan_key: PlanKey;
  plan_label: string;
  monthly_price_cents: number;
  monthly_report_limit: number;
  fresh_reports_used: number;
  fresh_reports_remaining: number;
  subscription_status: string;
  current_period_start: string;
  current_period_end: string;
  stripe_customer_exists: boolean;
  billing_management_available: boolean;
}

type UsageCounterRow = {
  used_count?: number | string | null;
};

type BillingCustomerRow = {
  stripe_customer_id?: string | null;
};

export async function loadAccountSummary({
  supabase,
  user,
  entitlement,
}: {
  supabase: SupabaseClient;
  user: User;
  entitlement: AccountEntitlement;
}): Promise<AccountSummary> {
  const plan = PLAN_DETAILS[entitlement.plan_key] ?? PLAN_DETAILS.free;
  const monthlyLimit = Number(entitlement.monthly_report_limit ?? plan.monthly_report_limit);
  const [usageResult, customerResult, billingEnabled] = await Promise.all([
    supabase
      .from("usage_counters")
      .select("used_count")
      .eq("account_id", entitlement.account_id)
      .eq("metric_key", "fresh_report")
      .eq("period_start", entitlement.current_period_start)
      .eq("period_end", entitlement.current_period_end)
      .maybeSingle(),
    supabase
      .from("billing_customers")
      .select("stripe_customer_id")
      .eq("account_id", entitlement.account_id)
      .maybeSingle(),
    getServerFeatureFlag(
      PRODUCT_FLAGS.billingCheckoutEnabled.key,
      PRODUCT_FLAGS.billingCheckoutEnabled.defaultValue,
      user.id,
      {
        account_id: entitlement.account_id,
        tier: entitlement.plan_key,
      },
    ),
  ]);

  if (usageResult.error) {
    throw new Error(`usage counters: ${usageResult.error.message}`);
  }
  if (customerResult.error) {
    throw new Error(`billing customer: ${customerResult.error.message}`);
  }

  const usage = usageResult.data as UsageCounterRow | null;
  const customer = customerResult.data as BillingCustomerRow | null;
  const used = Math.max(0, Number(usage?.used_count ?? 0));
  const limit = Math.max(0, monthlyLimit);

  return {
    account_id: entitlement.account_id,
    email: user.email ?? "Account owner",
    plan_key: entitlement.plan_key,
    plan_label: plan.label,
    monthly_price_cents: plan.monthly_price_cents,
    monthly_report_limit: limit,
    fresh_reports_used: used,
    fresh_reports_remaining: Math.max(0, limit - used),
    subscription_status: entitlement.subscription_status,
    current_period_start: entitlement.current_period_start,
    current_period_end: entitlement.current_period_end,
    stripe_customer_exists: Boolean(customer?.stripe_customer_id),
    billing_management_available: Boolean(billingEnabled),
  };
}

export function getPlanLabel(plan: PlanKey): string {
  return PLAN_DETAILS[plan]?.label ?? PLAN_DETAILS.free.label;
}
