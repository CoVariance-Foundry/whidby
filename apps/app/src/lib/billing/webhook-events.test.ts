import { describe, expect, it } from "vitest";
import { beginBillingWebhookEvent } from "./webhook-events";

type WebhookRow = {
  stripe_event_id: string;
  event_type: string;
  stripe_created_at: string;
  processing_status: "processing" | "processed" | "failed" | "ignored";
  attempt_count: number;
  last_error?: string | null;
};

class FakeWebhookTable {
  private result: WebhookRow | null | undefined;
  private updatePayload: Partial<WebhookRow> | null = null;
  private filters = new Map<string, unknown>();

  constructor(private readonly rows: Map<string, WebhookRow>) {}

  upsert(payload: WebhookRow) {
    if (this.rows.has(payload.stripe_event_id)) {
      this.result = null;
      return this;
    }
    this.rows.set(payload.stripe_event_id, payload);
    this.result = payload;
    return this;
  }

  update(payload: Partial<WebhookRow>) {
    this.updatePayload = payload;
    return this;
  }

  select() {
    return this;
  }

  eq(column: string, value: unknown) {
    this.filters.set(column, value);
    return this;
  }

  maybeSingle() {
    if (this.result !== undefined) {
      return { data: this.result, error: null };
    }

    const id = this.filters.get("stripe_event_id");
    if (typeof id !== "string") return { data: null, error: null };
    const row = this.rows.get(id);
    if (!row) return { data: null, error: null };

    const requiredStatus = this.filters.get("processing_status");
    if (requiredStatus && row.processing_status !== requiredStatus) {
      return { data: null, error: null };
    }

    if (this.updatePayload) {
      const updated = { ...row, ...this.updatePayload };
      this.rows.set(id, updated);
      return { data: updated, error: null };
    }

    return { data: row, error: null };
  }
}

class FakeSupabase {
  public rows = new Map<string, WebhookRow>();

  from() {
    return new FakeWebhookTable(this.rows);
  }
}

const eventParams = {
  stripe_event_id: "evt_123",
  event_type: "customer.subscription.updated",
  stripe_created_at: "2026-05-01T00:00:00.000Z",
};

describe("billing webhook event ledger", () => {
  it("claims a new webhook event for processing", async () => {
    const supabase = new FakeSupabase();

    const result = await beginBillingWebhookEvent(supabase as never, eventParams);

    expect(result.action).toBe("process");
    expect(result.record).toMatchObject({
      stripe_event_id: "evt_123",
      processing_status: "processing",
      attempt_count: 1,
    });
  });

  it("skips duplicate deliveries while the first delivery is processing", async () => {
    const supabase = new FakeSupabase();
    supabase.rows.set("evt_123", {
      ...eventParams,
      processing_status: "processing",
      attempt_count: 1,
    });

    const result = await beginBillingWebhookEvent(supabase as never, eventParams);

    expect(result.action).toBe("skip");
    expect(result.record).toMatchObject({
      stripe_event_id: "evt_123",
      processing_status: "processing",
      attempt_count: 1,
    });
  });

  it("reclaims failed webhook events for retry", async () => {
    const supabase = new FakeSupabase();
    supabase.rows.set("evt_123", {
      ...eventParams,
      processing_status: "failed",
      attempt_count: 1,
      last_error: "database unavailable",
    });

    const result = await beginBillingWebhookEvent(supabase as never, eventParams);

    expect(result.action).toBe("process");
    expect(result.record).toMatchObject({
      stripe_event_id: "evt_123",
      processing_status: "processing",
      attempt_count: 2,
      last_error: null,
    });
  });
});
