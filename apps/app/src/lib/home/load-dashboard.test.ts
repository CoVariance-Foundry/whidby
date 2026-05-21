import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  createClient: vi.fn(),
  resolveEntitlementContext: vi.fn(),
  loadAccountSummary: vi.fn(),
  loadStrategyCatalog: vi.fn(),
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

vi.mock("@/lib/account/summary", () => ({
  loadAccountSummary: mocks.loadAccountSummary,
}));

vi.mock("@/lib/strategies/catalog", () => ({
  loadStrategyCatalog: mocks.loadStrategyCatalog,
}));

import { EntitlementError } from "@/lib/account/entitlements";
import { loadDashboard } from "./load-dashboard";

const originalFetch = global.fetch;

const user = {
  id: "44444444-4444-4444-4444-444444444444",
  email: "owner@example.com",
};

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

const accountSummary = {
  account_id: entitlement.account_id,
  email: user.email,
  plan_key: "plus",
  plan_label: "Plus",
  monthly_price_cents: 4900,
  monthly_report_limit: 10,
  fresh_reports_used: 2,
  fresh_reports_remaining: 8,
  subscription_status: "active",
  cancel_at_period_end: false,
  current_period_start: entitlement.current_period_start,
  current_period_end: entitlement.current_period_end,
  stripe_customer_exists: true,
  billing_management_available: true,
};

const strategyCatalog = {
  strategies: [
    {
      strategy_id: "easy_win",
      name: "Easy Win",
      description: "Weak competition markets.",
      status: "launch",
      input_shape: "city_service",
    },
    {
      strategy_id: "gbp_blitz",
      name: "GBP Blitz",
      description: "Find GBP gaps.",
      status: "launch",
      input_shape: "city_service",
    },
    {
      strategy_id: "keyword_hijack",
      name: "Keyword Hijack",
      description: "Focus a primary keyword.",
      status: "launch",
      input_shape: "city_service_keyword",
    },
    {
      strategy_id: "expand_conquer",
      name: "Expand & Conquer",
      description: "Find lookalike expansion markets.",
      status: "launch",
      input_shape: "reference_city_service",
    },
    {
      strategy_id: "cash_cow",
      name: "Cash Cow",
      description: "Phase 2 lead economics.",
      status: "phase_2",
      input_shape: "cached_scan",
    },
  ],
  global_modifiers: [
    {
      modifier_id: "ai_resilience",
      name: "AI Resilience",
      behavior: "warn_not_hide",
    },
  ],
};

const reportsDashboard = {
  stats: {
    total_reports: 2,
    avg_score: 75,
    watchlist: 0,
    niches_scored: 2,
  },
  recent: [
    {
      id: "r1",
      niche: "roofing",
      city: "Phoenix, AZ",
      created_at: "2026-04-20T12:00:00Z",
    },
  ],
  recommended: [
    {
      id: "r1",
      niche: "roofing",
      city: "Phoenix, AZ",
      score: 78,
    },
  ],
  stat_cards: [
    { label: "Niches scored", value: "2" },
    { label: "Watchlist", value: "0" },
    { label: "Avg score", value: "75" },
    { label: "Reports", value: "2" },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  mocks.resolveEntitlementContext.mockResolvedValue({ user, entitlement });
  mocks.loadAccountSummary.mockResolvedValue(accountSummary);
  mocks.loadStrategyCatalog.mockResolvedValue(strategyCatalog);
  global.fetch = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({ status: "success", dashboard: reportsDashboard }),
      {
        status: 200,
        headers: { "content-type": "application/json" },
      },
    ),
  );
});

afterEach(() => {
  global.fetch = originalFetch;
  vi.restoreAllMocks();
});

describe("loadDashboard", () => {
  it("loads account summary, onboarding context, strategy catalog, and reports", async () => {
    const profile = {
      id: "profile-1",
      user_id: user.id,
      account_id: entitlement.account_id,
      recommended_strategy_id: "gbp_blitz",
      available_strategy_ids: ["gbp_blitz", "easy_win"],
      next_route: "/strategies",
      status: "strategy_recommended",
    };
    const target = {
      id: "target-1",
      onboarding_profile_id: "profile-1",
      strategy_id: "gbp_blitz",
      niche_keyword: "roofing",
      geo_scope: "city",
      city: "Phoenix",
      state: "AZ",
      resolved_label: "Phoenix, AZ",
      updated_at: "2026-05-16T12:00:00.000Z",
    };
    const supabase = createSupabaseMock({
      profileResult: { data: profile, error: null },
      targetResult: { data: target, error: null },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const dashboard = await loadDashboard({
      app_base_url: "https://app.example.test/",
    });

    expect(dashboard.stats).toEqual(reportsDashboard.stats);
    expect(dashboard.recent).toEqual(reportsDashboard.recent);
    expect(dashboard.recommended).toEqual(reportsDashboard.recommended);
    expect(dashboard.account).toMatchObject({
      status: "ready",
      summary: accountSummary,
      can_run_fresh_reports: true,
      entitlement: {
        account_id: entitlement.account_id,
        plan_key: "plus",
        fresh_report_quota_exempt: false,
      },
    });
    expect(dashboard.onboarding).toMatchObject({
      profile,
      target,
      starter_strategy_id: "gbp_blitz",
      shortcut_strategy_ids: ["gbp_blitz", "easy_win"],
      next_route: "/strategies",
      error: null,
    });
    expect(dashboard.strategies.starter.strategy_id).toBe("gbp_blitz");
    expect(dashboard.strategies.shortcuts.map((strategy) => strategy.strategy_id)).toEqual([
      "gbp_blitz",
      "easy_win",
    ]);
    expect(dashboard.strategies.catalog.strategies.map((strategy) => strategy.strategy_id)).toEqual([
      "easy_win",
      "gbp_blitz",
      "keyword_hijack",
      "expand_conquer",
    ]);
    expect(dashboard.report_error).toBeNull();
    expect(dashboard.multi_market_available).toBe(true);
    expect(mocks.createClient).toHaveBeenCalledOnce();
    expect(mocks.resolveEntitlementContext).toHaveBeenCalledWith(supabase);
    expect(mocks.loadAccountSummary).toHaveBeenCalledWith({
      supabase,
      user,
      entitlement,
    });
    expect(supabase.profileEq).toHaveBeenCalledWith("user_id", user.id);
    expect(supabase.targetEq).toHaveBeenCalledWith("onboarding_profile_id", "profile-1");
    expect(global.fetch).toHaveBeenCalledWith(
      "https://app.example.test/api/agent/reports?view=dashboard&limit=10",
      { cache: "no-store" },
    );
  });

  it("defaults empty onboarding to easy_win", async () => {
    const supabase = createSupabaseMock({
      profileResult: { data: null, error: null },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const dashboard = await loadDashboard({
      app_base_url: "https://app.example.test",
    });

    expect(dashboard.onboarding.profile).toBeNull();
    expect(dashboard.onboarding.target).toBeNull();
    expect(dashboard.onboarding.starter_strategy_id).toBe("easy_win");
    expect(dashboard.onboarding.shortcut_strategy_ids).toEqual(["easy_win"]);
    expect(dashboard.strategies.starter.strategy_id).toBe("easy_win");
    expect(supabase.targetMaybeSingle).not.toHaveBeenCalled();
  });

  it("falls back from phase-2 starter strategies and drops invalid shortcuts", async () => {
    const profile = {
      id: "profile-1",
      user_id: user.id,
      account_id: entitlement.account_id,
      recommended_strategy_id: "cash_cow",
      available_strategy_ids: [
        "cash_cow",
        "blue_ocean",
        "gbp_blitz",
        "portfolio_builder",
        "seasonal_arbitrage",
        "expand_conquer",
      ],
      next_route: "https://example.test/not-allowed",
    };
    const supabase = createSupabaseMock({
      profileResult: { data: profile, error: null },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const dashboard = await loadDashboard({
      app_base_url: "https://app.example.test",
    });

    expect(dashboard.onboarding.starter_strategy_id).toBe("easy_win");
    expect(dashboard.onboarding.shortcut_strategy_ids).toEqual([
      "easy_win",
      "gbp_blitz",
      "expand_conquer",
    ]);
    expect(dashboard.onboarding.next_route).toBe("/strategies");
    expect(dashboard.strategies.shortcuts.map((strategy) => strategy.strategy_id)).toEqual([
      "easy_win",
      "gbp_blitz",
      "expand_conquer",
    ]);
  });

  it("still loads reports when account summary loading fails after entitlement resolves", async () => {
    const supabase = createSupabaseMock({
      profileResult: { data: null, error: null },
    });
    mocks.createClient.mockResolvedValue(supabase);
    mocks.loadAccountSummary.mockRejectedValueOnce(
      new Error("usage counters: relation unavailable"),
    );

    const dashboard = await loadDashboard({
      app_base_url: "https://app.example.test",
    });

    expect(dashboard.account).toEqual({
      status: "error",
      error: { message: "usage counters: relation unavailable" },
      blocking: false,
      summary: null,
      entitlement: null,
      can_run_fresh_reports: false,
    });
    expect(dashboard.stats).toEqual(reportsDashboard.stats);
    expect(dashboard.recent).toEqual(reportsDashboard.recent);
    expect(dashboard.report_error).toBeNull();
    expect(global.fetch).toHaveBeenCalledWith(
      "https://app.example.test/api/agent/reports?view=dashboard&limit=10",
      { cache: "no-store" },
    );
  });

  it("does not load reports after unexpected onboarding context failures", async () => {
    const supabase = {
      from: vi.fn(() => {
        throw new Error("onboarding client unavailable");
      }),
    };
    mocks.createClient.mockResolvedValue(supabase);

    const dashboard = await loadDashboard({
      app_base_url: "https://app.example.test",
    });

    expect(dashboard.account).toEqual({
      status: "error",
      error: { message: "onboarding client unavailable" },
      blocking: true,
      summary: null,
      entitlement: null,
      can_run_fresh_reports: false,
    });
    expect(dashboard.recent).toEqual([]);
    expect(dashboard.report_error).toBeNull();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("can disable multi-market when the agency route is absent", async () => {
    const supabase = createSupabaseMock({
      profileResult: { data: null, error: null },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const dashboard = await loadDashboard({
      app_base_url: "https://app.example.test",
      multi_market_available: false,
    });

    expect(dashboard.multi_market_available).toBe(false);
  });

  it("returns usable account and strategy state when reports fetch fails", async () => {
    const supabase = createSupabaseMock({
      profileResult: { data: null, error: null },
    });
    mocks.createClient.mockResolvedValue(supabase);
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "unavailable" }), { status: 502 }),
    );

    const dashboard = await loadDashboard({
      app_base_url: "https://app.example.test",
    });

    expect(dashboard.account.status).toBe("ready");
    expect(dashboard.strategies.starter.strategy_id).toBe("easy_win");
    expect(dashboard.recent).toEqual([]);
    expect(dashboard.recommended).toEqual([]);
    expect(dashboard.stats.total_reports).toBe(0);
    expect(dashboard.report_error).toEqual({
      message: "Reports request failed with HTTP 502.",
    });
  });

  it("returns fallback reports when the reports BFF returns invalid JSON", async () => {
    const supabase = createSupabaseMock({
      profileResult: { data: null, error: null },
    });
    mocks.createClient.mockResolvedValue(supabase);
    global.fetch = vi.fn().mockResolvedValue(
      new Response("not-json", {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const dashboard = await loadDashboard({
      app_base_url: "https://app.example.test",
    });

    expect(dashboard.account.status).toBe("ready");
    expect(dashboard.recent).toEqual([]);
    expect(dashboard.recommended).toEqual([]);
    expect(dashboard.stats.total_reports).toBe(0);
    expect(dashboard.report_error).toEqual({
      message: "Reports response was invalid JSON.",
    });
  });

  it("returns an account error dashboard when entitlement resolution fails", async () => {
    const authError = new EntitlementError(
      "Authentication required.",
      401,
      "auth_required",
    );
    const supabase = createSupabaseMock();
    mocks.createClient.mockResolvedValue(supabase);
    mocks.resolveEntitlementContext.mockRejectedValueOnce(authError);

    const dashboard = await loadDashboard({
      app_base_url: "https://app.example.test",
    });

    expect(dashboard.account).toEqual({
      status: "error",
      error: {
        message: "Authentication required.",
        code: "auth_required",
        status: 401,
      },
      blocking: true,
      summary: null,
      entitlement: null,
      can_run_fresh_reports: false,
    });
    expect(dashboard.onboarding.profile).toBeNull();
    expect(dashboard.onboarding.starter_strategy_id).toBe("easy_win");
    expect(dashboard.recent).toEqual([]);
    expect(dashboard.recommended).toEqual([]);
    expect(dashboard.report_error).toBeNull();
    expect(global.fetch).not.toHaveBeenCalled();
    expect(mocks.loadAccountSummary).not.toHaveBeenCalled();
  });
});

type QueryResult = {
  data: unknown;
  error: { message: string } | null;
};

function createSupabaseMock(options: {
  profileResult?: QueryResult;
  targetResult?: QueryResult;
} = {}) {
  const profileResult = options.profileResult ?? { data: null, error: null };
  const targetResult = options.targetResult ?? { data: null, error: null };

  const profileMaybeSingle = vi.fn().mockResolvedValue(profileResult);
  const profileEq = vi.fn(() => ({ maybeSingle: profileMaybeSingle }));
  const profileSelect = vi.fn(() => ({ eq: profileEq }));

  const targetMaybeSingle = vi.fn().mockResolvedValue(targetResult);
  const targetLimit = vi.fn(() => ({ maybeSingle: targetMaybeSingle }));
  const targetOrder = vi.fn(() => ({ limit: targetLimit }));
  const targetEq = vi.fn(() => ({ order: targetOrder }));
  const targetSelect = vi.fn(() => ({ eq: targetEq }));

  return {
    profileEq,
    profileMaybeSingle,
    targetEq,
    targetOrder,
    targetLimit,
    targetMaybeSingle,
    from: vi.fn((table: string) => {
      if (table === "onboarding_profiles") {
        return {
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
