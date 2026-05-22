import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  createClient: vi.fn(),
  createAdminClient: vi.fn(),
  resolveEntitlementContext: vi.fn(),
  consumeReportQuotaUnits: vi.fn(),
  refundReportQuotaUnits: vi.fn(),
  consumeReportQuota: vi.fn(),
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
    consumeReportQuota: mocks.consumeReportQuota,
    consumeReportQuotaUnits: mocks.consumeReportQuotaUnits,
    refundReportQuotaUnits: mocks.refundReportQuotaUnits,
    resolveEntitlementContext: mocks.resolveEntitlementContext,
  };
});

import { POST } from "./route";

describe("POST /api/competitor-intel/runs", () => {
  const user = { id: "44444444-4444-4444-4444-444444444444" };
  const entitlement = {
    account_id: "33333333-3333-3333-3333-333333333333",
    member_role: "owner",
    plan_key: "plus",
    monthly_report_limit: 10,
    fresh_report_quota_exempt: false,
    subscription_status: "active",
    cancel_at_period_end: false,
    current_period_start: "2026-05-01T00:00:00.000Z",
    current_period_end: "2026-06-01T00:00:00.000Z",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    delete process.env.NEXT_PUBLIC_API_URL;
    delete process.env.STRATEGY_DISCOVERY_INTERNAL_TOKEN;
    mocks.createClient.mockResolvedValue({ rpc: vi.fn() });
    mocks.createAdminClient.mockReturnValue({ rpc: vi.fn() });
    mocks.resolveEntitlementContext.mockResolvedValue({ user, entitlement });
    mocks.consumeReportQuotaUnits.mockResolvedValue(true);
    mocks.refundReportQuotaUnits.mockResolvedValue(undefined);
    global.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          run_id: "competitor-run-1",
          status: "queued",
          state: "ready_to_run",
          quota_consumed: 2,
        }),
        { status: 200 },
      ),
    );
  });

  it("blocks free users before quota or upstream work", async () => {
    mocks.resolveEntitlementContext.mockResolvedValueOnce({
      user,
      entitlement: { ...entitlement, plan_key: "free", monthly_report_limit: 0 },
    });
    const req = new Request("http://localhost/api/competitor-intel/runs", {
      method: "POST",
      body: JSON.stringify({ city: "Boise", state: "ID", service: "roofing" }),
    });

    const res = await POST(req as never);

    expect(res.status).toBe(403);
    expect(await res.json()).toMatchObject({
      status: "upgrade_required",
      code: "competitor_intel_requires_paid_plan",
    });
    expect(mocks.consumeReportQuotaUnits).not.toHaveBeenCalled();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("uses one atomic 2-scan helper for paid runs", async () => {
    const req = new Request("http://localhost/api/competitor-intel/runs", {
      method: "POST",
      body: JSON.stringify({ city: "Boise", state: "ID", service: "roofing" }),
    });

    const res = await POST(req as never);

    expect(res.status).toBe(200);
    expect(mocks.consumeReportQuotaUnits).toHaveBeenCalledWith(
      expect.anything(),
      "33333333-3333-3333-3333-333333333333",
      2,
    );
    expect(mocks.consumeReportQuota).not.toHaveBeenCalled();
    const init = vi.mocked(global.fetch).mock.calls[0][1] as RequestInit;
    expect(JSON.parse(init.body as string)).toMatchObject({
      city: "Boise",
      state: "ID",
      service: "roofing",
      quota_consumed: 2,
      account_id: "33333333-3333-3333-3333-333333333333",
      created_by_user_id: "44444444-4444-4444-4444-444444444444",
    });
  });

  it("returns insufficient scans without fetching upstream", async () => {
    mocks.consumeReportQuotaUnits.mockResolvedValueOnce(false);
    const req = new Request("http://localhost/api/competitor-intel/runs", {
      method: "POST",
      body: JSON.stringify({ city: "Boise", state: "ID", service: "roofing" }),
    });

    const res = await POST(req as never);

    expect(res.status).toBe(429);
    expect(await res.json()).toMatchObject({
      status: "quota_exceeded",
      required_scans: 2,
    });
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("allows quota-exempt pro runs without consuming scans", async () => {
    mocks.resolveEntitlementContext.mockResolvedValueOnce({
      user,
      entitlement: {
        ...entitlement,
        plan_key: "pro",
        fresh_report_quota_exempt: true,
      },
    });
    const req = new Request("http://localhost/api/competitor-intel/runs", {
      method: "POST",
      body: JSON.stringify({ cbsa_code: "13820", service: "roofing" }),
    });

    const res = await POST(req as never);

    expect(res.status).toBe(200);
    expect(mocks.consumeReportQuotaUnits).not.toHaveBeenCalled();
    const init = vi.mocked(global.fetch).mock.calls[0][1] as RequestInit;
    expect(JSON.parse(init.body as string)).toMatchObject({
      cbsa_code: "13820",
      service: "roofing",
      quota_consumed: 0,
    });
  });

  it("refunds 2 scans when upstream fails after quota consumption", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "competitor run failed" }), {
        status: 503,
      }),
    );
    const req = new Request("http://localhost/api/competitor-intel/runs", {
      method: "POST",
      body: JSON.stringify({ city: "Boise", state: "ID", service: "roofing" }),
    });

    const res = await POST(req as never);

    expect(res.status).toBe(503);
    expect(mocks.refundReportQuotaUnits).toHaveBeenCalledWith(
      expect.anything(),
      "33333333-3333-3333-3333-333333333333",
      2,
    );
  });
});
