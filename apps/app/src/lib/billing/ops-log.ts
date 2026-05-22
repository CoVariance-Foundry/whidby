import type { SupabaseClient } from "@supabase/supabase-js";

export type BillingIssueSeverity = "critical" | "error" | "warning" | "info";

export type BillingIssueParams = {
  severity: BillingIssueSeverity;
  event_type: string;
  source: string;
  public_message: string;
  internal_message?: string | null;
  account_id?: string | null;
  user_id?: string | null;
  stripe_customer_id?: string | null;
  stripe_subscription_id?: string | null;
  stripe_checkout_session_id?: string | null;
  stripe_event_id?: string | null;
  metadata?: Record<string, unknown>;
};

export function errorToInternalMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error);
}

export async function recordBillingOperationEvent(
  supabase: SupabaseClient,
  params: BillingIssueParams,
): Promise<void> {
  try {
    const { error } = await supabase.from("billing_operation_events").insert({
      severity: params.severity,
      status: "open",
      event_type: params.event_type,
      source: params.source,
      account_id: params.account_id ?? null,
      user_id: params.user_id ?? null,
      stripe_customer_id: params.stripe_customer_id ?? null,
      stripe_subscription_id: params.stripe_subscription_id ?? null,
      stripe_checkout_session_id: params.stripe_checkout_session_id ?? null,
      stripe_event_id: params.stripe_event_id ?? null,
      public_message: params.public_message,
      internal_message: params.internal_message ?? null,
      metadata: params.metadata ?? {},
      updated_at: new Date().toISOString(),
    });
    if (error) {
      console.warn("[billing/ops-log] insert failed", error.message);
    }
  } catch (error) {
    console.warn("[billing/ops-log] skipped", errorToInternalMessage(error));
  }
}
