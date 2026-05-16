import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  createClient: vi.fn(),
  resolveEntitlementContext: vi.fn(),
  consumeReportQuota: vi.fn(),
  refundReportQuota: vi.fn(),
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: mocks.createClient,
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
    consumeReportQuota: mocks.consumeReportQuota,
    refundReportQuota: mocks.refundReportQuota,
    resolveEntitlementContext: mocks.resolveEntitlementContext,
  };
});

import { POST } from "./route";

describe("POST /api/strategies/runs", () => {
  const user = {
    id: "44444444-4444-4444-4444-444444444444",
    email: "user@example.com",
  };
  const entitlement = {
    account_id: "33333333-3333-3333-3333-333333333333",
    member_role: "owner",
    plan_key: "plus",
    monthly_report_limit: 10,
    subscription_status: "active",
    current_period_start: "2026-05-01T00:00:00.000Z",
    current_period_end: "2026-06-01T00:00:00.000Z",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    delete process.env.NEXT_PUBLIC_API_URL;
    mocks.createClient.mockResolvedValue({ rpc: vi.fn() });
    mocks.resolveEntitlementContext.mockResolvedValue({ user, entitlement });
    mocks.consumeReportQuota.mockResolvedValue(true);
    mocks.refundReportQuota.mockResolvedValue(undefined);
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ run_id: "strategy-run-1", status: "queued" }), {
        status: 200,
      }),
    );
  });

  it("blocks free fresh requests before fetching upstream", async () => {
    mocks.resolveEntitlementContext.mockResolvedValueOnce({
      user,
      entitlement: { ...entitlement, plan_key: "free", monthly_report_limit: 0 },
    });
    const req = new Request("http://localhost/api/strategies/runs", {
      method: "POST",
      body: JSON.stringify({ mode: "fresh", strategy_id: "easy_win" }),
    });

    const res = await POST(req as never);

    expect(res.status).toBe(403);
    expect(await res.json()).toMatchObject({
      code: "fresh_strategy_runs_not_included",
      monthly_report_limit: 0,
      tier: "free",
    });
    expect(global.fetch).not.toHaveBeenCalled();
    expect(mocks.consumeReportQuota).not.toHaveBeenCalled();
  });

  it("allows cached free requests and injects account and user ids", async () => {
    mocks.resolveEntitlementContext.mockResolvedValueOnce({
      user,
      entitlement: { ...entitlement, plan_key: "free", monthly_report_limit: 0 },
    });
    const req = new Request("http://localhost/api/strategies/runs", {
      method: "POST",
      body: JSON.stringify({ strategy_id: "gbp_blitz", limit: 25 }),
    });

    const res = await POST(req as never);

    expect(res.status).toBe(200);
    const init = vi.mocked(global.fetch).mock.calls[0][1] as RequestInit;
    expect(vi.mocked(global.fetch).mock.calls[0][0]).toBe(
      "http://localhost:8000/api/strategy-runs",
    );
    expect(JSON.parse(init.body as string)).toEqual({
      strategy_id: "gbp_blitz",
      limit: 25,
      mode: "cached",
      account_id: "33333333-3333-3333-3333-333333333333",
      created_by_user_id: "44444444-4444-4444-4444-444444444444",
    });
    expect(mocks.consumeReportQuota).not.toHaveBeenCalled();
  });

  it("allows paid fresh requests and injects account and user ids", async () => {
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test";
    const req = new Request("http://localhost/api/strategies/runs", {
      method: "POST",
      body: JSON.stringify({
        mode: "fresh",
        strategy_id: "keyword_hijack",
        primary_keyword: "boise plumber",
      }),
    });

    const res = await POST(req as never);

    expect(res.status).toBe(200);
    const init = vi.mocked(global.fetch).mock.calls[0][1] as RequestInit;
    expect(vi.mocked(global.fetch).mock.calls[0][0]).toBe(
      "https://api.example.test/api/strategy-runs",
    );
    expect(JSON.parse(init.body as string)).toMatchObject({
      mode: "fresh",
      strategy_id: "keyword_hijack",
      primary_keyword: "boise plumber",
      account_id: "33333333-3333-3333-3333-333333333333",
      created_by_user_id: "44444444-4444-4444-4444-444444444444",
    });
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
    expect(init.cache).toBe("no-store");
    expect(mocks.consumeReportQuota).toHaveBeenCalledWith(
      expect.anything(),
      "33333333-3333-3333-3333-333333333333",
    );
  });

  it("normalizes legacy lens_id to strategy_id for upstream runs", async () => {
    const req = new Request("http://localhost/api/strategies/runs", {
      method: "POST",
      body: JSON.stringify({ mode: "cached", lens_id: "easy_win" }),
    });

    await POST(req as never);

    const init = vi.mocked(global.fetch).mock.calls[0][1] as RequestInit;
    expect(JSON.parse(init.body as string)).toMatchObject({
      strategy_id: "easy_win",
      mode: "cached",
    });
    expect(JSON.parse(init.body as string)).not.toHaveProperty("lens_id");
  });

  it("blocks paid fresh requests when quota is exhausted", async () => {
    mocks.consumeReportQuota.mockResolvedValueOnce(false);
    const req = new Request("http://localhost/api/strategies/runs", {
      method: "POST",
      body: JSON.stringify({ mode: "fresh", strategy_id: "easy_win" }),
    });

    const res = await POST(req as never);

    expect(res.status).toBe(429);
    expect(await res.json()).toMatchObject({
      code: "monthly_report_quota_exceeded",
    });
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("refunds consumed quota when upstream rejects a fresh run", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "invalid strategy run" }), {
        status: 400,
      }),
    );
    const req = new Request("http://localhost/api/strategies/runs", {
      method: "POST",
      body: JSON.stringify({ mode: "fresh", strategy_id: "easy_win" }),
    });

    const res = await POST(req as never);

    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({ detail: "invalid strategy run" });
    expect(mocks.refundReportQuota).toHaveBeenCalledWith(
      expect.anything(),
      "33333333-3333-3333-3333-333333333333",
    );
  });

  it("rejects fresh runs over the 100 target cap before consuming quota", async () => {
    const targets = Array.from({ length: 101 }, (_, index) => ({
      cbsa_code: String(index),
      niche_normalized: "roofing",
    }));
    const req = new Request("http://localhost/api/strategies/runs", {
      method: "POST",
      body: JSON.stringify({ mode: "fresh", strategy_id: "easy_win", targets }),
    });

    const res = await POST(req as never);

    expect(res.status).toBe(400);
    expect(await res.json()).toMatchObject({
      status: "validation_error",
    });
    expect(mocks.consumeReportQuota).not.toHaveBeenCalled();
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
