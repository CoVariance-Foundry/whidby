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

const entitlement = {
  account_id: "33333333-3333-3333-3333-333333333333",
  member_role: "owner",
  plan_key: "plus",
  monthly_report_limit: 10,
  subscription_status: "active",
  current_period_start: "2026-05-01T00:00:00.000Z",
  current_period_end: "2026-06-01T00:00:00.000Z",
};

function makeSupabaseMock(
  responses: Array<{ data: Array<Record<string, unknown>> | null; error: { message: string } | null }>,
  v2Response: { data: Array<Record<string, unknown>> | null; error: { message: string } | null } = {
    data: [],
    error: null,
  },
) {
  const limit = vi.fn();
  for (const response of responses) {
    limit.mockResolvedValueOnce(response);
  }
  const order = vi.fn(() => ({ limit }));
  const is = vi.fn(() => ({ order }));
  const or = vi.fn(() => ({ is, order }));
  const reportsSelect = vi.fn(() => ({ or }));

  const inFilter = vi.fn().mockResolvedValue(v2Response);
  const v2Select = vi.fn(() => ({ in: inFilter }));

  const from = vi.fn((table: string) => {
    if (table === "metro_score_v2") {
      return { select: v2Select };
    }
    return { select: reportsSelect };
  });
  return { from, reportsSelect, or, is, order, limit, v2Select, inFilter };
}

describe("GET /api/agent/reports", () => {
  const rows = [
    {
      id: "r1",
      niche_keyword: "roofing",
      geo_target: "Phoenix, AZ",
      created_at: "2026-04-20T12:00:00Z",
      spec_version: "1.1",
      metros: [{ scores: { opportunity: 78 } }],
      access_scope: "account",
      owner_account_id: entitlement.account_id,
    },
    {
      id: "r2",
      niche_keyword: "plumbing",
      geo_target: "Austin, TX",
      created_at: "2026-04-19T09:00:00Z",
      spec_version: "1.1",
      metros: [{ scores: { opportunity: 71 } }],
      access_scope: "cached",
      owner_account_id: null,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    mocks.resolveEntitlementContext.mockResolvedValue({
      user: { id: "44444444-4444-4444-4444-444444444444" },
      entitlement,
    });
  });

  it("returns report table rows and dashboard DTOs from the reports table", async () => {
    const query = makeSupabaseMock([{ data: rows, error: null }]);
    mocks.createClient.mockResolvedValue({ from: query.from });

    const req = new NextRequest("http://localhost/api/agent/reports?limit=10");
    const res = await GET(req);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.status).toBe("success");
    expect(body.reports[0]).toMatchObject({
      id: "r1",
      niche: "roofing",
      city: "Phoenix, AZ",
      opportunity_score: 78,
    });
    expect(body.dashboard.stats).toMatchObject({
      total_reports: 2,
      avg_score: 75,
      watchlist: 0,
      niches_scored: 2,
    });
    expect(body.dashboard.recommended).toHaveLength(2);
    expect(query.is).toHaveBeenCalledWith("archived_at", null);
    expect(query.or).toHaveBeenCalledWith(
      `access_scope.eq.cached,owner_account_id.eq.${entitlement.account_id}`,
    );
    expect(query.limit).toHaveBeenCalledWith(10);
    expect(query.inFilter).toHaveBeenCalledWith("report_id", ["r1", "r2"]);
  });

  it("explicitly filters non-cached reports owned by another account", async () => {
    const query = makeSupabaseMock([
      {
        data: [
          ...rows,
          {
            id: "r3",
            niche_keyword: "hvac",
            geo_target: "Denver, CO",
            created_at: "2026-04-18T09:00:00Z",
            spec_version: "1.1",
            metros: [{ scores: { opportunity: 88 } }],
            access_scope: "account",
            owner_account_id: "99999999-9999-9999-9999-999999999999",
          },
        ],
        error: null,
      },
    ]);
    mocks.createClient.mockResolvedValue({ from: query.from });

    const req = new NextRequest("http://localhost/api/agent/reports");
    const res = await GET(req);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.reports.map((row: { id: string }) => row.id)).toEqual(["r1", "r2"]);
    expect(query.inFilter).toHaveBeenCalledWith("report_id", ["r1", "r2"]);
  });

  it("preserves report opportunity scores for V2 report rows", async () => {
    const query = makeSupabaseMock([{ data: rows, error: null }], {
      data: [{ report_id: "r1", spec_version: "2.0" }],
      error: null,
    });
    mocks.createClient.mockResolvedValue({ from: query.from });

    const req = new NextRequest("http://localhost/api/agent/reports");
    const res = await GET(req);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.reports[0]).toMatchObject({
      id: "r1",
      spec_version: "2.0",
      opportunity_score: 78,
      archetype_id: "PACK_VULN",
    });
    expect(body.dashboard.recommended[0]).toMatchObject({
      id: "r1",
      score: 78,
    });
    expect(body.dashboard.stats.avg_score).toBe(75);
  });

  it("retries without archived_at when the migration is missing", async () => {
    const query = makeSupabaseMock([
      { data: null, error: { message: "column reports.archived_at does not exist" } },
      { data: rows.slice(0, 1), error: null },
    ]);
    mocks.createClient.mockResolvedValue({ from: query.from });

    const req = new NextRequest("http://localhost/api/agent/reports");
    const res = await GET(req);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.reports).toHaveLength(1);
    expect(query.is).toHaveBeenCalledTimes(1);
    expect(query.order).toHaveBeenCalledTimes(2);
  });

  it("returns a 502 envelope for non-archived_at query errors", async () => {
    const query = makeSupabaseMock([
      { data: null, error: { message: "permission denied" } },
    ]);
    mocks.createClient.mockResolvedValue({ from: query.from });

    const req = new NextRequest("http://localhost/api/agent/reports");
    const res = await GET(req);
    const body = await res.json();

    expect(res.status).toBe(502);
    expect(body).toMatchObject({
      status: "unavailable",
      message: "reports list: permission denied",
    });
  });
});
