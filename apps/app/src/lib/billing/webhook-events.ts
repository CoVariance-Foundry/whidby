import type { SupabaseClient } from "@supabase/supabase-js";

export type BillingWebhookEventRecord = {
  stripe_event_id: string;
  event_type: string;
  stripe_created_at: string;
  processing_status: "processing" | "processed" | "failed" | "ignored";
  attempt_count: number;
};

export type BillingWebhookBeginResult =
  | { action: "skip"; record: BillingWebhookEventRecord }
  | { action: "process"; record: BillingWebhookEventRecord };

export async function beginBillingWebhookEvent(
  supabase: SupabaseClient,
  params: {
    stripe_event_id: string;
    event_type: string;
    stripe_created_at: string;
  },
): Promise<BillingWebhookBeginResult> {
  const projection =
    "stripe_event_id, event_type, stripe_created_at, processing_status, attempt_count";

  const { data: inserted, error: insertError } = await supabase
    .from("billing_webhook_events")
    .upsert(
      {
        stripe_event_id: params.stripe_event_id,
        event_type: params.event_type,
        stripe_created_at: params.stripe_created_at,
        processing_status: "processing",
        attempt_count: 1,
        updated_at: new Date().toISOString(),
      },
      {
        onConflict: "stripe_event_id",
        ignoreDuplicates: true,
      },
    )
    .select(projection)
    .maybeSingle();
  if (insertError) throw new Error(`webhook event insert failed: ${insertError.message}`);

  if (inserted) {
    return { action: "process", record: inserted as BillingWebhookEventRecord };
  }

  const { data: existing, error: readError } = await supabase
    .from("billing_webhook_events")
    .select(projection)
    .eq("stripe_event_id", params.stripe_event_id)
    .maybeSingle();
  if (readError) throw new Error(`webhook event lookup failed: ${readError.message}`);
  if (!existing) throw new Error(`webhook event ${params.stripe_event_id} was not inserted`);

  const record = existing as BillingWebhookEventRecord;
  if (
    record.processing_status === "processed" ||
    record.processing_status === "ignored" ||
    record.processing_status === "processing"
  ) {
    return { action: "skip", record };
  }

  const { data: retry, error: retryError } = await supabase
    .from("billing_webhook_events")
    .update({
      processing_status: "processing",
      attempt_count: Number(record.attempt_count ?? 0) + 1,
      last_error: null,
      updated_at: new Date().toISOString(),
    })
    .eq("stripe_event_id", params.stripe_event_id)
    .eq("processing_status", "failed")
    .select(projection)
    .maybeSingle();
  if (retryError) throw new Error(`webhook event retry failed: ${retryError.message}`);

  if (retry) return { action: "process", record: retry as BillingWebhookEventRecord };
  return { action: "skip", record };
}

export async function finishBillingWebhookEvent(
  supabase: SupabaseClient,
  stripeEventId: string,
  params: {
    status: "processed" | "failed" | "ignored";
    error?: string | null;
  },
): Promise<void> {
  const { error } = await supabase
    .from("billing_webhook_events")
    .update({
      processing_status: params.status,
      last_error: params.error ?? null,
      processed_at: params.status === "failed" ? null : new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
    .eq("stripe_event_id", stripeEventId);
  if (error) throw new Error(`webhook event finish failed: ${error.message}`);
}
