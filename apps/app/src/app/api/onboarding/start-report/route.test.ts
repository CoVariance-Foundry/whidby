import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  createClient: vi.fn(),
  resolveEntitlementContext: vi.fn(),
  scoringPost: vi.fn(),
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

vi.mock("../../agent/scoring/route", () => ({
  POST: mocks.scoringPost,
}));

import { POST } from "./route";

describe("/api/onboarding/start-report", () => {
  const user = {
    id: "44444444-4444-4444-4444-444444444444",
    email: "user@example.com",
  };
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
    global.fetch = vi.fn();
    mocks.resolveEntitlementContext.mockResolvedValue({ user, entitlement });
    mocks.scoringPost.mockResolvedValue(
      new Response(JSON.stringify({ status: "success", report_id: "report-1" }), {
        status: 200,
      }),
    );
  });

  it("returns 403 for free entitlement without calling scoring", async () => {
    const supabase = createSupabaseMock({
      targetResult: {
        data: createTarget(),
        error: null,
      },
    });
    mocks.createClient.mockResolvedValue(supabase);
    mocks.resolveEntitlementContext.mockResolvedValueOnce({
      user,
      entitlement: { ...entitlement, plan_key: "free", monthly_report_limit: 0 },
    });

    const req = new Request("http://localhost/api/onboarding/start-report", {
      method: "POST",
      body: JSON.stringify({}),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(403);
    expect(body).toMatchObject({
      status: "tier_limit",
      code: "fresh_reports_not_included",
      tier: "free",
      monthly_report_limit: 0,
    });
    expect(supabase.profileUpdate).toHaveBeenCalledWith(
      expect.objectContaining({
        status: "upgrade_required",
        next_route: "/onboarding",
      }),
    );
    expect(supabase.profileUpdateEq).toHaveBeenCalledWith("id", "profile-1");
    expect(mocks.scoringPost).not.toHaveBeenCalled();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("delegates quota-exempt free admin city targets to scoring", async () => {
    const target = createTarget({
      city: "Phoenix",
      state: "AZ",
    });
    const supabase = createSupabaseMock({
      targetResult: { data: target, error: null },
    });
    mocks.createClient.mockResolvedValue(supabase);
    mocks.resolveEntitlementContext.mockResolvedValueOnce({
      user: { ...user, email: "admin-test@widby.dev" },
      entitlement: {
        ...entitlement,
        member_role: "admin",
        plan_key: "free",
        monthly_report_limit: 0,
        fresh_report_quota_exempt: true,
      },
    });

    const req = new Request("http://localhost/api/onboarding/start-report", {
      method: "POST",
      body: JSON.stringify({}),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toMatchObject({
      status: "success",
      report_id: "report-1",
      redirect_url: "/reports/report-1?generating=true",
    });
    expect(supabase.profileUpdate).toHaveBeenCalledWith(
      expect.objectContaining({
        status: "report_queued",
        next_route: "/reports/report-1?generating=true",
      }),
    );
    expect(mocks.scoringPost).toHaveBeenCalledOnce();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("returns cached guidance for state targets without calling scoring", async () => {
    const target = createTarget({
      geo_scope: "state",
      city: null,
      state: "AZ",
      resolved_label: "Arizona",
    });
    const supabase = createSupabaseMock({
      targetResult: { data: target, error: null },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const req = new Request("http://localhost/api/onboarding/start-report", {
      method: "POST",
      body: JSON.stringify({ strategy_id: "easy_win" }),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toEqual({
      status: "cached_route_selected",
      code: "broad_target_uses_cached_explore",
      message: "Broad onboarding targets use cached market discovery before fresh city scoring.",
      redirect_url: "/explore",
      target,
    });
    expect(supabase.profileUpdate).toHaveBeenCalledWith(
      expect.objectContaining({
        status: "cached_route_selected",
        next_route: "/explore",
      }),
    );
    expect(supabase.profileUpdateEq).toHaveBeenCalledWith("id", "profile-1");
    expect(supabase.targetEq).toHaveBeenCalledWith("strategy_id", "easy_win");
    expect(mocks.scoringPost).not.toHaveBeenCalled();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("returns cached guidance for free entitlement with a state target", async () => {
    const target = createTarget({
      geo_scope: "state",
      city: null,
      state: "AZ",
      resolved_label: "Arizona",
    });
    const supabase = createSupabaseMock({
      targetResult: { data: target, error: null },
    });
    mocks.createClient.mockResolvedValue(supabase);
    mocks.resolveEntitlementContext.mockResolvedValueOnce({
      user,
      entitlement: { ...entitlement, plan_key: "free", monthly_report_limit: 0 },
    });

    const req = new Request("http://localhost/api/onboarding/start-report", {
      method: "POST",
      body: JSON.stringify({}),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toEqual({
      status: "cached_route_selected",
      code: "broad_target_uses_cached_explore",
      message: "Broad onboarding targets use cached market discovery before fresh city scoring.",
      redirect_url: "/explore",
      target,
    });
    expect(supabase.profileUpdate).toHaveBeenCalledWith(
      expect.objectContaining({
        status: "cached_route_selected",
        next_route: "/explore",
      }),
    );
    expect(mocks.scoringPost).not.toHaveBeenCalled();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("returns 400 for non-string target_id", async () => {
    const supabase = createSupabaseMock();
    mocks.createClient.mockResolvedValue(supabase);

    const req = new Request("http://localhost/api/onboarding/start-report", {
      method: "POST",
      body: JSON.stringify({ target_id: 123 }),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(400);
    expect(body).toEqual({
      status: "validation_error",
      message: "target_id must be a string when provided.",
    });
    expect(supabase.profileMaybeSingle).not.toHaveBeenCalled();
    expect(mocks.scoringPost).not.toHaveBeenCalled();
  });

  it("delegates city targets to the existing scoring contract", async () => {
    const target = createTarget({
      city: "Phoenix",
      state: "AZ",
      place_id: "place.123",
      dataforseo_location_code: 1012873,
      metadata_source: "mapbox_selected",
    });
    const supabase = createSupabaseMock({
      targetResult: { data: target, error: null },
    });
    mocks.createClient.mockResolvedValue(supabase);
    mocks.scoringPost.mockImplementation(async (req: Request) => {
      const payload = await req.json();
      return new Response(
        JSON.stringify({
          status: "success",
          report_id: "report-123",
          query: payload,
        }),
        { status: 200 },
      );
    });

    const req = new Request("http://localhost/api/onboarding/start-report", {
      method: "POST",
      headers: { "x-request-id": "request-123" },
      body: JSON.stringify({ target_id: "target-1" }),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toEqual({
      status: "success",
      report_id: "report-123",
      redirect_url: "/reports/report-123?generating=true",
      scoring: {
        status: "success",
        report_id: "report-123",
        query: {
          city: "Phoenix",
          service: "roofing",
          state: "AZ",
          place_id: "place.123",
          dataforseo_location_code: 1012873,
          metadata_source: "mapbox_selected",
        },
      },
    });
    expect(supabase.targetEq).toHaveBeenCalledWith("id", "target-1");
    expect(supabase.profileUpdate).toHaveBeenCalledWith(
      expect.objectContaining({
        status: "report_queued",
        next_route: "/reports/report-123?generating=true",
      }),
    );
    expect(supabase.profileUpdateEq).toHaveBeenCalledWith("id", "profile-1");
    expect(mocks.scoringPost).toHaveBeenCalledOnce();
    const scoringReq = mocks.scoringPost.mock.calls[0][0] as Request;
    expect(scoringReq.headers.get("x-request-id")).toBe("request-123");
  });
});

type QueryResult = {
  data: unknown;
  error: { message: string } | null;
};

function createTarget(overrides: Record<string, unknown> = {}) {
  return {
    id: "target-1",
    strategy_id: "easy_win",
    niche_keyword: "roofing",
    geo_scope: "city",
    city: "Phoenix",
    state: "AZ",
    place_id: null,
    dataforseo_location_code: null,
    resolved_label: null,
    metadata_source: "typed",
    ...overrides,
  };
}

function createSupabaseMock(options: {
  profileResult?: QueryResult;
  targetResult?: QueryResult;
} = {}) {
  const profileResult = options.profileResult ?? { data: { id: "profile-1" }, error: null };
  const targetResult = options.targetResult ?? { data: createTarget(), error: null };

  const profileMaybeSingle = vi.fn().mockResolvedValue(profileResult);
  const profileEq = vi.fn(() => ({ maybeSingle: profileMaybeSingle }));
  const profileSelect = vi.fn(() => ({ eq: profileEq }));
  const profileUpdateEq = vi.fn().mockResolvedValue({ error: null });
  const profileUpdate = vi.fn(() => ({ eq: profileUpdateEq }));

  const targetMaybeSingle = vi.fn().mockResolvedValue(targetResult);
  const targetLimit = vi.fn(() => ({ maybeSingle: targetMaybeSingle }));
  const targetOrder = vi.fn(() => ({ limit: targetLimit }));
  const targetEq = vi.fn(() => targetBuilder);
  const targetBuilder = {
    eq: targetEq,
    order: targetOrder,
  };
  const targetSelect = vi.fn(() => targetBuilder);

  return {
    profileEq,
    profileMaybeSingle,
    profileUpdate,
    profileUpdateEq,
    targetEq,
    targetOrder,
    targetLimit,
    targetMaybeSingle,
    from: vi.fn((table: string) => {
      if (table === "onboarding_profiles") {
        return {
          select: profileSelect,
          update: profileUpdate,
        };
      }
      if (table === "onboarding_targets") {
        return {
          select: targetSelect,
        };
      }
      throw new Error(`Unexpected table ${table}`);
    }),
  };
}
