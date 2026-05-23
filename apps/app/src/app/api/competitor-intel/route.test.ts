import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  createClient: vi.fn(),
  resolveEntitlementContext: vi.fn(),
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
    resolveEntitlementContext: mocks.resolveEntitlementContext,
  };
});

import { GET } from "./route";

describe("GET /api/competitor-intel", () => {
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
    mocks.resolveEntitlementContext.mockResolvedValue({ user, entitlement });
    global.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          status: "ready_to_run",
          target: { niche_normalized: "roofing", cbsa_code: "13820" },
          monthly_report_limit: 10,
        }),
        { status: 200 },
      ),
    );
  });

  it("returns upgrade_required for free users without fetching upstream facts", async () => {
    mocks.resolveEntitlementContext.mockResolvedValueOnce({
      user,
      entitlement: { ...entitlement, plan_key: "free", monthly_report_limit: 0 },
    });
    const req = new Request("http://localhost/api/competitor-intel?city=Boise&service=roofing");

    const res = await GET(req as never);

    expect(res.status).toBe(200);
    expect(await res.json()).toMatchObject({
      status: "upgrade_required",
      code: "competitor_intel_requires_paid_plan",
      tier: "free",
    });
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("allows plus/pro users to fetch ready state through FastAPI", async () => {
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test";
    process.env.STRATEGY_DISCOVERY_INTERNAL_TOKEN = "secret-token";
    const req = new Request(
      "http://localhost/api/competitor-intel?city=Boise&state=ID&service=roofing",
    );

    const res = await GET(req as never);

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({
      status: "ready_to_run",
      target: { niche_normalized: "roofing", cbsa_code: "13820" },
      monthly_report_limit: 10,
    });
    expect(global.fetch).toHaveBeenCalledWith(
      "https://api.example.test/api/competitor-intel?city=Boise&state=ID&service=roofing&account_id=33333333-3333-3333-3333-333333333333",
      expect.objectContaining({
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer secret-token",
        },
      }),
    );
  });

  it("preserves snake_case response keys from the upstream read model", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          status: "aggregate_only",
          target: { niche_normalized: "roofing" },
          summary: { local_difficulty: 41, avg_top5_da: 27.5 },
          facts: { keyword_fact_count: 3 },
        }),
        { status: 200 },
      ),
    );
    const req = new Request("http://localhost/api/competitor-intel?city=Boise&service=roofing");

    const res = await GET(req as never);

    expect(await res.json()).toEqual({
      status: "aggregate_only",
      target: { niche_normalized: "roofing" },
      summary: { local_difficulty: 41, avg_top5_da: 27.5 },
      facts: { keyword_fact_count: 3 },
    });
  });
});
