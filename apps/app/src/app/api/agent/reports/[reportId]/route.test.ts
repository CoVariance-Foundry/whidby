import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

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

describe("GET /api/agent/reports/[reportId]", () => {
  const entitlement = {
    account_id: "33333333-3333-3333-3333-333333333333",
    member_role: "owner",
    plan_key: "plus",
    monthly_report_limit: 10,
    subscription_status: "active",
    current_period_start: "2026-05-01T00:00:00.000Z",
    current_period_end: "2026-06-01T00:00:00.000Z",
  };

  let maybeSingle: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    maybeSingle = vi.fn().mockResolvedValue({
      data: {
        id: "r1",
        access_scope: "account",
        owner_account_id: entitlement.account_id,
      },
      error: null,
    });
    mocks.createClient.mockResolvedValue({
      from: vi.fn(() => ({
        select: vi.fn(() => ({
          eq: vi.fn(() => ({ maybeSingle })),
        })),
      })),
    });
    mocks.resolveEntitlementContext.mockResolvedValue({
      user: { id: "44444444-4444-4444-4444-444444444444" },
      entitlement,
    });
  });

  it("maps upstream niche payload into report detail shape", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          report_id: "r1",
          generated_at: "2026-05-14T18:00:00Z",
          spec_version: "1.1",
          input: {
            niche_keyword: "roofing",
            geo_scope: "city",
            geo_target: "Phoenix, AZ",
            report_depth: "standard",
            strategy_profile: "balanced",
          },
          keyword_expansion: { expanded_keywords: [] },
          metros: [],
          meta: { total_api_calls: 7 },
        }),
        { status: 200 },
      ),
    );

    const req = new NextRequest("http://localhost/api/agent/reports/r1");
    const res = await GET(req, { params: Promise.resolve({ reportId: "r1" }) });
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.status).toBe("success");
    expect(body.report).toMatchObject({
      id: "r1",
      niche_keyword: "roofing",
      geo_target: "Phoenix, AZ",
      strategy_profile: "balanced",
    });
  });

  it("returns 502 envelope when upstream request fails", async () => {
    maybeSingle.mockResolvedValueOnce({
      data: {
        id: "missing",
        access_scope: "account",
        owner_account_id: entitlement.account_id,
      },
      error: null,
    });
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "report not found" }), { status: 404 }),
    );

    const req = new NextRequest("http://localhost/api/agent/reports/missing");
    const res = await GET(req, { params: Promise.resolve({ reportId: "missing" }) });
    const body = await res.json();

    expect(res.status).toBe(502);
    expect(body.status).toBe("unavailable");
    expect(body.upstream_status).toBe(404);
  });

  it("returns 502 envelope when upstream request times out", async () => {
    global.fetch = vi.fn().mockRejectedValue(new DOMException("aborted", "AbortError"));

    const req = new NextRequest("http://localhost/api/agent/reports/r1");
    const res = await GET(req, { params: Promise.resolve({ reportId: "r1" }) });
    const body = await res.json();

    expect(res.status).toBe(502);
    expect(body.status).toBe("unavailable");
    expect(body.message).toContain("timed out");
  });

  it("does not proxy reports owned by another account", async () => {
    maybeSingle.mockResolvedValueOnce({
      data: {
        id: "other-report",
        access_scope: "account",
        owner_account_id: "99999999-9999-9999-9999-999999999999",
      },
      error: null,
    });
    global.fetch = vi.fn();

    const req = new NextRequest("http://localhost/api/agent/reports/other-report");
    const res = await GET(req, { params: Promise.resolve({ reportId: "other-report" }) });
    const body = await res.json();

    expect(res.status).toBe(404);
    expect(body.status).toBe("not_found");
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("allows cached reports through the upstream reader", async () => {
    maybeSingle.mockResolvedValueOnce({
      data: {
        id: "cached-report",
        access_scope: "cached",
        owner_account_id: null,
      },
      error: null,
    });
    global.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          report_id: "cached-report",
          generated_at: "2026-05-14T18:00:00Z",
          input: { niche_keyword: "plumbing" },
          metros: [],
        }),
        { status: 200 },
      ),
    );

    const req = new NextRequest("http://localhost/api/agent/reports/cached-report");
    const res = await GET(req, { params: Promise.resolve({ reportId: "cached-report" }) });
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.report.id).toBe("cached-report");
  });
});
