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

import { POST } from "./route";

describe("/api/onboarding/target", () => {
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
    mocks.resolveEntitlementContext.mockResolvedValue({ user, entitlement });
  });

  it("returns 400 when required fields are missing", async () => {
    const supabase = createSupabaseMock();
    mocks.createClient.mockResolvedValue(supabase);

    const req = new Request("http://localhost/api/onboarding/target", {
      method: "POST",
      body: JSON.stringify({ strategy_id: "easy_win", geo_scope: "city", city: "Phoenix" }),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(400);
    expect(body).toEqual({
      status: "validation_error",
      message: "niche_keyword is required.",
    });
    expect(supabase.profileMaybeSingle).not.toHaveBeenCalled();
  });

  it("returns 400 when city target lacks city and resolved_label", async () => {
    const supabase = createSupabaseMock();
    mocks.createClient.mockResolvedValue(supabase);

    const req = new Request("http://localhost/api/onboarding/target", {
      method: "POST",
      body: JSON.stringify({
        strategy_id: "easy_win",
        niche_keyword: "roofing",
        geo_scope: "city",
      }),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(400);
    expect(body).toEqual({
      status: "validation_error",
      message: "city targets must include city or resolved_label.",
    });
    expect(supabase.profileMaybeSingle).not.toHaveBeenCalled();
  });

  it("returns 400 for invalid strategy_id before profile lookup", async () => {
    const supabase = createSupabaseMock();
    mocks.createClient.mockResolvedValue(supabase);

    const req = new Request("http://localhost/api/onboarding/target", {
      method: "POST",
      body: JSON.stringify({
        strategy_id: "not_real",
        niche_keyword: "roofing",
        geo_scope: "city",
        city: "Phoenix",
      }),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(400);
    expect(body).toEqual({
      status: "validation_error",
      message:
        "strategy_id must be one of easy_win, gbp_blitz, expand_conquer, keyword_hijack.",
    });
    expect(supabase.profileMaybeSingle).not.toHaveBeenCalled();
    expect(supabase.targetUpsert).not.toHaveBeenCalled();
  });

  it("returns 409 for visible locked strategy_id before profile lookup", async () => {
    const supabase = createSupabaseMock();
    mocks.createClient.mockResolvedValue(supabase);

    const req = new Request("http://localhost/api/onboarding/target", {
      method: "POST",
      body: JSON.stringify({
        strategy_id: "portfolio_builder",
        niche_keyword: "roofing",
        geo_scope: "city",
        city: "Phoenix",
      }),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(409);
    expect(body).toEqual({
      status: "locked_strategy",
      code: "strategy_locked",
      message:
        "Portfolio Builder is visible as a locked path node and cannot be selected as an onboarding target yet.",
    });
    expect(supabase.profileMaybeSingle).not.toHaveBeenCalled();
    expect(supabase.targetUpsert).not.toHaveBeenCalled();
  });

  it("upserts a valid target and updates profile status", async () => {
    const profile = { id: "profile-1" };
    const target = {
      id: "target-1",
      onboarding_profile_id: "profile-1",
      strategy_id: "easy_win",
      niche_keyword: "roofing",
      geo_scope: "city",
      city: "Phoenix",
      state: "AZ",
    };
    const supabase = createSupabaseMock({
      profileResult: { data: profile, error: null },
      targetResult: { data: target, error: null },
      updateResult: { data: null, error: null },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const req = new Request("http://localhost/api/onboarding/target", {
      method: "POST",
      body: JSON.stringify({
        strategy_id: "easy_win",
        niche_keyword: "roofing",
        service_category_id: "home_services",
        geo_scope: "city",
        city: "Phoenix",
        state: "AZ",
        place_id: "place.123",
        dataforseo_location_code: 1012873,
        metadata_source: "mapbox_selected",
      }),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toEqual({ status: "success", target });
    expect(supabase.profileEq).toHaveBeenCalledWith("user_id", user.id);
    expect(supabase.targetUpsert).toHaveBeenCalledWith(
      {
        onboarding_profile_id: "profile-1",
        strategy_id: "easy_win",
        niche_keyword: "roofing",
        service_category_id: "home_services",
        geo_scope: "city",
        city: "Phoenix",
        state: "AZ",
        cbsa_code: null,
        place_id: "place.123",
        dataforseo_location_code: 1012873,
        resolved_label: null,
        metadata_source: "mapbox_selected",
      },
      { onConflict: "onboarding_profile_id,strategy_id" },
    );
    expect(supabase.profileUpdate).toHaveBeenCalledWith({ status: "target_selected" });
    expect(supabase.profileUpdateEq).toHaveBeenCalledWith("id", "profile-1");
  });
});

type QueryResult = {
  data: unknown;
  error: { message: string } | null;
};

function createSupabaseMock(options: {
  profileResult?: QueryResult;
  targetResult?: QueryResult;
  updateResult?: QueryResult;
} = {}) {
  const profileResult = options.profileResult ?? { data: { id: "profile-1" }, error: null };
  const targetResult = options.targetResult ?? { data: null, error: null };
  const updateResult = options.updateResult ?? { data: null, error: null };

  const profileMaybeSingle = vi.fn().mockResolvedValue(profileResult);
  const profileEq = vi.fn(() => ({ maybeSingle: profileMaybeSingle }));
  const profileSelect = vi.fn(() => ({ eq: profileEq }));

  const profileUpdateEq = vi.fn().mockResolvedValue(updateResult);
  const profileUpdate = vi.fn(() => ({ eq: profileUpdateEq }));

  const targetSingle = vi.fn().mockResolvedValue(targetResult);
  const targetSelectAfterUpsert = vi.fn(() => ({ single: targetSingle }));
  const targetUpsert = vi.fn(() => ({ select: targetSelectAfterUpsert }));

  return {
    profileEq,
    profileMaybeSingle,
    profileUpdate,
    profileUpdateEq,
    targetUpsert,
    from: vi.fn((table: string) => {
      if (table === "onboarding_profiles") {
        return {
          select: profileSelect,
          update: profileUpdate,
        };
      }
      if (table === "onboarding_targets") {
        return {
          upsert: targetUpsert,
        };
      }
      throw new Error(`Unexpected table ${table}`);
    }),
  };
}
