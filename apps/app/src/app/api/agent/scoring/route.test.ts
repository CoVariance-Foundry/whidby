import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  createClient: vi.fn(),
  createAdminClient: vi.fn(),
  resolveEntitlementContext: vi.fn(),
  consumeReportQuota: vi.fn(),
  refundReportQuota: vi.fn(),
  getServerFeatureFlag: vi.fn(),
  captureServerEvent: vi.fn(),
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: mocks.createClient,
}));

vi.mock("@/lib/supabase/admin", () => ({
  createAdminClient: mocks.createAdminClient,
}));

vi.mock("@/lib/account/entitlements", () => {
  class EntitlementError extends Error {
    constructor(
      message: string,
      public readonly status: number,
      public readonly code: string,
    ) {
      super(message);
    }
  }
  return {
    EntitlementError,
    resolveEntitlementContext: mocks.resolveEntitlementContext,
    consumeReportQuota: mocks.consumeReportQuota,
    refundReportQuota: mocks.refundReportQuota,
  };
});

vi.mock("@/lib/flags/server", () => ({
  getServerFeatureFlag: mocks.getServerFeatureFlag,
  captureServerEvent: mocks.captureServerEvent,
}));

import { POST } from "./route";

describe("POST /api/agent/scoring", () => {
  const entitlement = {
    account_id: "33333333-3333-3333-3333-333333333333",
    member_role: "owner",
    plan_key: "plus",
    monthly_report_limit: 10,
    fresh_report_quota_exempt: false,
    subscription_status: "active",
    current_period_start: "2026-05-01T00:00:00.000Z",
    current_period_end: "2026-06-01T00:00:00.000Z",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mocks.createClient.mockResolvedValue({ rpc: vi.fn() });
    mocks.createAdminClient.mockReturnValue({ rpc: vi.fn() });
    mocks.resolveEntitlementContext.mockResolvedValue({
      user: { id: "44444444-4444-4444-4444-444444444444", email: "user@example.com" },
      entitlement,
    });
    mocks.consumeReportQuota.mockResolvedValue(true);
    mocks.refundReportQuota.mockResolvedValue(undefined);
    mocks.getServerFeatureFlag.mockResolvedValue(true);
  });

  it("proxies to FastAPI and maps the response", async () => {
    const spy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        report_id: "r1",
        opportunity_score: 72,
        classification_label: "Medium",
        evidence: [],
        report: { input: { niche_keyword: "roofing" } },
      }), { status: 200 }),
    );
    global.fetch = spy;
    const req = new Request("http://localhost/api/agent/scoring", {
      method: "POST",
      body: JSON.stringify({ city: "Phoenix", service: "roofing", state: "AZ" }),
    });
    const res = await POST(req as never);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.score_result.opportunity_score).toBe(72);
    expect(body.score_result.classification_label).toBe("Medium");
    expect(body.report_id).toBe("r1");
    expect(body.query.metadata_source).toBe("typed");
    expect(body.fallback_path).toBe("city_state");
    expect(typeof body.request_id).toBe("string");
    const init = spy.mock.calls[0][1] as RequestInit;
    expect((init.headers as Record<string, string>)["x-request-id"]).toBeTruthy();
    expect(body.account.tier).toBe("plus");
    const sent = JSON.parse((vi.mocked(global.fetch).mock.calls[0][1] as RequestInit).body as string);
    expect(sent.owner_account_id).toBe("33333333-3333-3333-3333-333333333333");
    expect(sent.created_by_user_id).toBe("44444444-4444-4444-4444-444444444444");
    expect(sent.collection_profile).toBe("interactive");
  });

  it("blocks free users before calling FastAPI", async () => {
    mocks.resolveEntitlementContext.mockResolvedValueOnce({
      user: { id: "44444444-4444-4444-4444-444444444444", email: "user@example.com" },
      entitlement: { ...entitlement, plan_key: "free", monthly_report_limit: 0 },
    });
    global.fetch = vi.fn();
    const req = new Request("http://localhost/api/agent/scoring", {
      method: "POST",
      body: JSON.stringify({ city: "Phoenix", service: "roofing", state: "AZ" }),
    });
    const res = await POST(req as never);
    const body = await res.json();
    expect(res.status).toBe(403);
    expect(body.code).toBe("fresh_reports_not_included");
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("allows quota-exempt free admins without consuming quota", async () => {
    mocks.resolveEntitlementContext.mockResolvedValueOnce({
      user: {
        id: "55555555-5555-5555-5555-555555555555",
        email: "admin-test@widby.dev",
      },
      entitlement: {
        ...entitlement,
        member_role: "admin",
        plan_key: "free",
        monthly_report_limit: 0,
        fresh_report_quota_exempt: true,
      },
    });
    const spy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        report_id: "admin-report-1",
        opportunity_score: 91,
        classification_label: "High",
        evidence: [],
        report: { input: { niche_keyword: "roofing" } },
      }), { status: 200 }),
    );
    global.fetch = spy;
    const req = new Request("http://localhost/api/agent/scoring", {
      method: "POST",
      body: JSON.stringify({ city: "Phoenix", service: "roofing", state: "AZ" }),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.account.tier).toBe("free");
    expect(body.account.fresh_report_quota_exempt).toBe(true);
    expect(mocks.consumeReportQuota).not.toHaveBeenCalled();
    expect(spy).toHaveBeenCalledOnce();
  });

  it("blocks users who have exhausted monthly quota", async () => {
    mocks.consumeReportQuota.mockResolvedValueOnce(false);
    global.fetch = vi.fn();
    const req = new Request("http://localhost/api/agent/scoring", {
      method: "POST",
      body: JSON.stringify({ city: "Phoenix", service: "roofing", state: "AZ" }),
    });
    const res = await POST(req as never);
    const body = await res.json();
    expect(res.status).toBe(429);
    expect(body.code).toBe("monthly_report_quota_exceeded");
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("passes dry_run=true when NEXT_PUBLIC_NICHE_DRY_RUN=1", async () => {
    process.env.NEXT_PUBLIC_NICHE_DRY_RUN = "1";
    const spy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ report_id: "r2", opportunity_score: 50,
        classification_label: "Medium", evidence: [], report: { input: { niche_keyword: "x" }}}), { status: 200 }),
    );
    global.fetch = spy;
    const req = new Request("http://localhost/api/agent/scoring", {
      method: "POST",
      body: JSON.stringify({ city: "Phoenix", service: "roofing", state: "AZ" }),
    });
    await POST(req as never);
    const sent = JSON.parse((spy.mock.calls[0][1] as RequestInit).body as string);
    expect(sent.dry_run).toBe(true);
    delete process.env.NEXT_PUBLIC_NICHE_DRY_RUN;
  });

  it("forwards place_id and dataforseo_location_code when provided", async () => {
    const spy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        report_id: "r3",
        opportunity_score: 81,
        classification_label: "High",
        evidence: [],
        report: { input: { niche_keyword: "roofing" } },
      }), { status: 200 }),
    );
    global.fetch = spy;
    const req = new Request("http://localhost/api/agent/scoring", {
      method: "POST",
      body: JSON.stringify({
        city: "Paris",
        service: "roofing",
        place_id: "place.123",
        dataforseo_location_code: 12345,
      }),
    });
    await POST(req as never);

    const sent = JSON.parse((spy.mock.calls[0][1] as RequestInit).body as string);
    expect(sent.place_id).toBe("place.123");
    expect(sent.dataforseo_location_code).toBe(12345);
    expect(sent.metadata_source).toBe("typed");
  });

  it("forwards metadata_source when provided", async () => {
    const spy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        report_id: "r4",
        opportunity_score: 88,
        classification_label: "High",
        evidence: [],
        report: { input: { niche_keyword: "roofing" } },
      }), { status: 200 }),
    );
    global.fetch = spy;
    const req = new Request("http://localhost/api/agent/scoring", {
      method: "POST",
      body: JSON.stringify({
        city: "Phoenix",
        service: "roofing",
        metadata_source: "mapbox_selected",
      }),
    });
    await POST(req as never);

    const sent = JSON.parse((spy.mock.calls[0][1] as RequestInit).body as string);
    expect(sent.metadata_source).toBe("mapbox_selected");
  });

  it("preserves Explore fallback_cbsa scan metadata through quota-protected proxy", async () => {
    const spy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        report_id: "r5",
        opportunity_score: 79,
        classification_label: "High",
        evidence: [],
        report: { input: { niche_keyword: "roofing" } },
      }), { status: 200 }),
    );
    global.fetch = spy;
    const req = new Request("http://localhost/api/agent/scoring", {
      method: "POST",
      body: JSON.stringify({
        city: "Phoenix-Mesa-Chandler",
        service: "roofing",
        state: "AZ",
        metadata_source: "fallback_cbsa",
      }),
    });
    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.query).toMatchObject({
      city: "Phoenix-Mesa-Chandler",
      service: "roofing",
      state: "AZ",
      metadata_source: "fallback_cbsa",
    });
    expect(body.fallback_path).toBe("city_state");
    const sent = JSON.parse((spy.mock.calls[0][1] as RequestInit).body as string);
    expect(sent).toMatchObject({
      niche: "roofing",
      city: "Phoenix-Mesa-Chandler",
      state: "AZ",
      metadata_source: "fallback_cbsa",
      owner_account_id: "33333333-3333-3333-3333-333333333333",
      created_by_user_id: "44444444-4444-4444-4444-444444444444",
      collection_profile: "interactive",
    });
  });

  it("aborts FastAPI after 58 seconds and refunds quota once", async () => {
    vi.useFakeTimers();
    const controller = new AbortController();
    const timeout = vi
      .spyOn(AbortSignal, "timeout")
      .mockImplementation((milliseconds: number) => {
        setTimeout(() => {
          controller.abort(new DOMException("upstream timeout", "TimeoutError"));
        }, milliseconds);
        return controller.signal;
      });
    global.fetch = vi.fn((_url, init) => {
      const signal = (init as RequestInit).signal as AbortSignal;
      return new Promise((_resolve, reject) => {
        signal.addEventListener("abort", () => reject(signal.reason), { once: true });
      });
    }) as typeof fetch;
    const req = new Request("http://localhost/api/agent/scoring", {
      method: "POST",
      body: JSON.stringify({ city: "Phoenix", service: "roofing", state: "AZ" }),
    });

    try {
      const pending = POST(req as never);
      await vi.advanceTimersByTimeAsync(57_999);
      expect(mocks.refundReportQuota).not.toHaveBeenCalled();
      await vi.advanceTimersByTimeAsync(1);
      const response = await pending;

      expect(timeout).toHaveBeenCalledWith(58_000);
      expect(response.status).toBe(502);
      expect(mocks.refundReportQuota).toHaveBeenCalledTimes(1);
      expect(mocks.refundReportQuota).toHaveBeenCalledWith(
        expect.any(Object),
        entitlement.account_id,
      );
    } finally {
      timeout.mockRestore();
      vi.useRealTimers();
    }
  });
});
