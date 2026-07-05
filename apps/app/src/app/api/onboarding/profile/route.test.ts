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

import { EntitlementError } from "@/lib/account/entitlements";
import { GET, POST } from "./route";

describe("/api/onboarding/profile", () => {
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

  it("returns 401 for unauthenticated requests", async () => {
    mocks.createClient.mockResolvedValue(createSupabaseMock());
    mocks.resolveEntitlementContext.mockRejectedValueOnce(
      new EntitlementError("Authentication required.", 401, "auth_required"),
    );

    const req = new Request("http://localhost/api/onboarding/profile", {
      method: "POST",
      body: JSON.stringify({ intent: "find_first" }),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(401);
    expect(body).toEqual({
      status: "entitlement_error",
      code: "auth_required",
      message: "Authentication required.",
    });
  });

  it("upserts one profile with routing fields", async () => {
    const profile = {
      id: "profile-1",
      user_id: user.id,
      account_id: entitlement.account_id,
      intent: "scale",
      focus: "revenue",
      recommended_strategy_id: "expand_conquer",
      available_strategy_ids: [
        "expand_conquer",
        "easy_win",
        "gbp_blitz",
        "keyword_hijack",
        "portfolio_builder",
      ],
      next_route: "/strategies",
      status: "strategy_recommended",
    };
    const supabase = createSupabaseMock({
      upsertResult: { data: profile, error: null },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const req = new Request("http://localhost/api/onboarding/profile", {
      method: "POST",
      body: JSON.stringify({
        intent: "scale",
        focus: "revenue",
        referral_source: "newsletter",
      }),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.status).toBe("success");
    expect(body.profile).toEqual(profile);
    expect(body.routing).toMatchObject({
      starter: "expand_conquer",
      next_route: "/strategies",
    });
    expect(supabase.profileUpsert).toHaveBeenCalledOnce();
    const [profileUpsertPayload, profileUpsertOptions] = supabase.profileUpsert.mock
      .calls[0] as unknown as [
      {
        available_strategy_ids: string[];
        completed_at: string;
        [key: string]: unknown;
      },
      { onConflict: string },
    ];
    expect(profileUpsertPayload).toMatchObject({
      user_id: user.id,
      account_id: entitlement.account_id,
      intent: "scale",
      focus: "revenue",
      coach_or_agency: null,
      referral_source: "newsletter",
      recommended_strategy_id: "expand_conquer",
      next_route: "/strategies",
      status: "strategy_recommended",
    });
    expect(profileUpsertPayload.available_strategy_ids).toContain("expand_conquer");
    expect(profileUpsertPayload.available_strategy_ids).not.toEqual(
      expect.arrayContaining(["cash_cow", "blue_ocean", "seasonal_arbitrage"]),
    );
    expect(profileUpsertPayload.completed_at).toEqual(expect.any(String));
    expect(profileUpsertOptions).toEqual({ onConflict: "user_id" });
  });

  it("persists first-segment users with the dashboard as their first surface", async () => {
    const profile = {
      id: "profile-1",
      user_id: user.id,
      account_id: entitlement.account_id,
      intent: "find_first",
      focus: "niche",
      recommended_strategy_id: "easy_win",
      available_strategy_ids: ["easy_win", "gbp_blitz", "keyword_hijack"],
      next_route: "/",
      status: "strategy_recommended",
    };
    const supabase = createSupabaseMock({
      upsertResult: { data: profile, error: null },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const req = new Request("http://localhost/api/onboarding/profile", {
      method: "POST",
      body: JSON.stringify({
        intent: "find_first",
        focus: "niche",
      }),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.routing).toMatchObject({
      starter: "easy_win",
      next_route: "/",
    });
    expect(supabase.profileUpsert).toHaveBeenCalledOnce();
    const [profileUpsertPayload] = supabase.profileUpsert.mock.calls[0] as unknown as [
      { next_route: string; user_id: string; account_id: string },
    ];
    expect(profileUpsertPayload).toMatchObject({
      user_id: user.id,
      account_id: entitlement.account_id,
      next_route: "/",
    });
  });

  it("returns 400 for invalid intent and does not upsert", async () => {
    const supabase = createSupabaseMock();
    mocks.createClient.mockResolvedValue(supabase);

    const req = new Request("http://localhost/api/onboarding/profile", {
      method: "POST",
      body: JSON.stringify({ intent: "not_real" }),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(400);
    expect(body.status).toBe("validation_error");
    expect(supabase.profileUpsert).not.toHaveBeenCalled();
  });

  it("returns 400 for non-string focus and does not upsert", async () => {
    const supabase = createSupabaseMock();
    mocks.createClient.mockResolvedValue(supabase);

    const req = new Request("http://localhost/api/onboarding/profile", {
      method: "POST",
      body: JSON.stringify({ intent: "find_first", focus: 123 }),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(400);
    expect(body).toMatchObject({
      status: "validation_error",
      message: "focus must be a string when provided.",
    });
    expect(supabase.profileUpsert).not.toHaveBeenCalled();
  });

  it("returns 400 for non-string referral_source and does not upsert", async () => {
    const supabase = createSupabaseMock();
    mocks.createClient.mockResolvedValue(supabase);

    const req = new Request("http://localhost/api/onboarding/profile", {
      method: "POST",
      body: JSON.stringify({ intent: "find_first", referral_source: { channel: "ad" } }),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(400);
    expect(body).toMatchObject({
      status: "validation_error",
      message: "referral_source must be a string when provided.",
    });
    expect(supabase.profileUpsert).not.toHaveBeenCalled();
  });

  it("returns 400 for unknown focus and does not upsert", async () => {
    const supabase = createSupabaseMock();
    mocks.createClient.mockResolvedValue(supabase);

    const req = new Request("http://localhost/api/onboarding/profile", {
      method: "POST",
      body: JSON.stringify({ intent: "scale", focus: "something_else" }),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(400);
    expect(body.status).toBe("validation_error");
    expect(body.message).toContain("focus must be one of");
    expect(supabase.profileUpsert).not.toHaveBeenCalled();
  });

  it("returns profile plus latest target when present", async () => {
    const profile = {
      id: "profile-1",
      user_id: user.id,
      intent: "find_first",
      status: "strategy_recommended",
    };
    const target = {
      id: "target-1",
      onboarding_profile_id: "profile-1",
      niche_keyword: "roofing",
      updated_at: "2026-05-16T12:00:00.000Z",
    };
    const supabase = createSupabaseMock({
      profileResult: { data: profile, error: null },
      targetResult: { data: target, error: null },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const res = await GET();
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toEqual({ status: "success", profile, target });
    expect(supabase.profileEq).toHaveBeenCalledWith("user_id", user.id);
    expect(supabase.targetEq).toHaveBeenCalledWith("onboarding_profile_id", profile.id);
    expect(supabase.targetOrder).toHaveBeenCalledWith("updated_at", { ascending: false });
    expect(supabase.targetLimit).toHaveBeenCalledWith(1);
  });

  it("returns empty when no profile exists", async () => {
    const supabase = createSupabaseMock({
      profileResult: { data: null, error: null },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const res = await GET();
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toEqual({ status: "empty", profile: null, target: null });
    expect(supabase.targetMaybeSingle).not.toHaveBeenCalled();
  });
});

type QueryResult = {
  data: unknown;
  error: { message: string } | null;
};

function createSupabaseMock(options: {
  upsertResult?: QueryResult;
  profileResult?: QueryResult;
  targetResult?: QueryResult;
} = {}) {
  const upsertResult = options.upsertResult ?? { data: null, error: null };
  const profileResult = options.profileResult ?? { data: null, error: null };
  const targetResult = options.targetResult ?? { data: null, error: null };

  const profileSingle = vi.fn().mockResolvedValue(upsertResult);
  const profileSelectAfterUpsert = vi.fn(() => ({ single: profileSingle }));
  const profileUpsert = vi.fn(() => ({ select: profileSelectAfterUpsert }));

  const profileMaybeSingle = vi.fn().mockResolvedValue(profileResult);
  const profileEq = vi.fn(() => ({ maybeSingle: profileMaybeSingle }));
  const profileSelect = vi.fn(() => ({ eq: profileEq }));

  const targetMaybeSingle = vi.fn().mockResolvedValue(targetResult);
  const targetLimit = vi.fn(() => ({ maybeSingle: targetMaybeSingle }));
  const targetOrder = vi.fn(() => ({ limit: targetLimit }));
  const targetEq = vi.fn(() => ({ order: targetOrder }));
  const targetSelect = vi.fn(() => ({ eq: targetEq }));

  return {
    profileUpsert,
    profileEq,
    profileMaybeSingle,
    targetEq,
    targetOrder,
    targetLimit,
    targetMaybeSingle,
    from: vi.fn((table: string) => {
      if (table === "onboarding_profiles") {
        return {
          upsert: profileUpsert,
          select: profileSelect,
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
