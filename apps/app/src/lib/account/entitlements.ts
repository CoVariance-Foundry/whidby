import type { SupabaseClient, User } from "@supabase/supabase-js";

export type PlanKey = "free" | "plus" | "pro";

export interface AccountEntitlement {
  account_id: string;
  member_role: string;
  plan_key: PlanKey;
  monthly_report_limit: number;
  fresh_report_quota_exempt: boolean;
  subscription_status: string;
  cancel_at_period_end: boolean;
  current_period_start: string;
  current_period_end: string;
}

export interface EntitlementContext {
  user: User;
  entitlement: AccountEntitlement;
}

export async function resolveEntitlementContext(
  supabase: SupabaseClient,
): Promise<EntitlementContext> {
  const {
    data: { user },
    error: userError,
  } = await supabase.auth.getUser();

  if (userError || !user) {
    throw new EntitlementError("Authentication required.", 401, "auth_required");
  }

  const { data, error } = await supabase.rpc("get_account_entitlement");
  if (error) {
    throw new EntitlementError(
      "Unable to resolve account entitlement.",
      500,
      "entitlement_unavailable",
    );
  }

  const row = Array.isArray(data) ? data[0] : data;
  if (!row?.account_id) {
    throw new EntitlementError(
      "No account is available for this user.",
      500,
      "account_unavailable",
    );
  }

  return {
    user,
    entitlement: {
      account_id: String(row.account_id),
      member_role: String(row.member_role ?? "owner"),
      plan_key: normalizePlanKey(row.plan_key),
      monthly_report_limit: Number(row.monthly_report_limit ?? 0),
      fresh_report_quota_exempt: row.fresh_report_quota_exempt === true,
      subscription_status: String(row.subscription_status ?? "active"),
      cancel_at_period_end: row.cancel_at_period_end === true,
      current_period_start: String(row.current_period_start ?? ""),
      current_period_end: String(row.current_period_end ?? ""),
    },
  };
}

export async function consumeReportQuota(
  supabase: SupabaseClient,
  accountId: string,
): Promise<boolean> {
  const { data, error } = await supabase.rpc("consume_report_quota", {
    p_account_id: accountId,
  });
  if (error) {
    throw new EntitlementError(
      "Unable to consume report quota.",
      500,
      "quota_unavailable",
    );
  }
  return data === true;
}

export async function refundReportQuota(
  supabase: SupabaseClient,
  accountId: string,
): Promise<void> {
  const { error } = await supabase.rpc("refund_report_quota", {
    p_account_id: accountId,
  });
  if (error) {
    console.warn("[entitlements] quota refund failed", error.message);
  }
}

export class EntitlementError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code: string,
  ) {
    super(message);
  }
}

function normalizePlanKey(value: unknown): PlanKey {
  return value === "plus" || value === "pro" ? value : "free";
}
