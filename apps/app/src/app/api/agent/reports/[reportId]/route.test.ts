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
  let reportsSelect: ReturnType<typeof vi.fn>;
  let v2Limit: ReturnType<typeof vi.fn>;
  const reportRow = {
    id: "r1",
    created_at: "2026-05-14T18:00:00Z",
    spec_version: "1.1",
    niche_keyword: "roofing",
    geo_scope: "city",
    geo_target: "Phoenix, AZ",
    report_depth: "standard",
    strategy_profile: "balanced",
    resolved_weights: { organic: 0.6, local: 0.4 },
    keyword_expansion: { expanded_keywords: [] },
    metros: [],
    meta: { source: "supabase" },
    access_scope: "account",
    owner_account_id: entitlement.account_id,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    maybeSingle = vi.fn().mockResolvedValue({
      data: reportRow,
      error: null,
    });
    v2Limit = vi.fn().mockResolvedValue({
      data: [],
      error: null,
    });
    reportsSelect = vi.fn(() => ({
      eq: vi.fn(() => ({ maybeSingle })),
    }));
    const v2Select = vi.fn(() => ({
      eq: vi.fn(() => ({ limit: v2Limit })),
    }));
    mocks.createClient.mockResolvedValue({
      from: vi.fn((table: string) => ({
        select: table === "metro_score_v2" ? v2Select : reportsSelect,
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
    expect(reportsSelect).toHaveBeenCalledWith(expect.stringContaining("meta"));
    expect(body.report).toMatchObject({
      id: "r1",
      niche_keyword: "roofing",
      geo_target: "Phoenix, AZ",
      strategy_profile: "balanced",
      meta: { total_api_calls: 7 },
    });
  });

  it("overlays V2 score version when report has metro_score_v2 rows", async () => {
    v2Limit.mockResolvedValueOnce({
      data: [{ spec_version: "2.0" }],
      error: null,
    });
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
        }),
        { status: 200 },
      ),
    );

    const req = new NextRequest("http://localhost/api/agent/reports/r1");
    const res = await GET(req, { params: Promise.resolve({ reportId: "r1" }) });
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.status).toBe("success");
    expect(body.report.spec_version).toBe("2.0");
  });

  it("keeps report details available when V2 version lookup fails", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    try {
      v2Limit.mockResolvedValueOnce({
        data: null,
        error: { message: "connection error" },
      });
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
          }),
          { status: 200 },
        ),
      );

      const req = new NextRequest("http://localhost/api/agent/reports/r1");
      const res = await GET(req, { params: Promise.resolve({ reportId: "r1" }) });
      const body = await res.json();

      expect(res.status).toBe(200);
      expect(body.status).toBe("success");
      expect(body.report.spec_version).toBe("1.1");
      expect(warn).toHaveBeenCalledWith(
        "[agent/reports] failed to resolve V2 score version",
        { report_id: "r1", message: "connection error" },
      );
    } finally {
      warn.mockRestore();
    }
  });

  it("falls back to the Supabase report row when upstream returns non-ok", async () => {
    maybeSingle.mockResolvedValueOnce({
      data: {
        ...reportRow,
        id: "missing",
      },
      error: null,
    });
    v2Limit.mockResolvedValueOnce({
      data: [{ spec_version: "2.0" }],
      error: null,
    });
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "report not found" }), { status: 404 }),
    );

    const req = new NextRequest("http://localhost/api/agent/reports/missing");
    const res = await GET(req, { params: Promise.resolve({ reportId: "missing" }) });
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.status).toBe("success");
    expect(body.upstream_status).toBe(404);
    expect(body.report).toMatchObject({
      id: "missing",
      niche_keyword: "roofing",
      geo_target: "Phoenix, AZ",
      resolved_weights: { organic: 0.6, local: 0.4 },
      meta: { source: "supabase" },
      spec_version: "2.0",
      access_scope: "account",
      owner_account_id: entitlement.account_id,
    });
  });

  it("falls back to the Supabase report row when upstream returns invalid JSON", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response("this is not json", {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
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
      resolved_weights: { organic: 0.6, local: 0.4 },
      meta: { source: "supabase" },
      access_scope: "account",
      owner_account_id: entitlement.account_id,
    });
  });

  it("falls back to the Supabase report row when upstream request times out", async () => {
    global.fetch = vi.fn().mockRejectedValue(new DOMException("aborted", "AbortError"));

    const req = new NextRequest("http://localhost/api/agent/reports/r1");
    const res = await GET(req, { params: Promise.resolve({ reportId: "r1" }) });
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.status).toBe("success");
    expect(body.report).toMatchObject({
      id: "r1",
      niche_keyword: "roofing",
      geo_target: "Phoenix, AZ",
      meta: { source: "supabase" },
    });
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
