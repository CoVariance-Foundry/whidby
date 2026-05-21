// @vitest-environment jsdom
import React from "react";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import HomePage from "./page";
import { loadDashboard, type DashboardData } from "@/lib/home/load-dashboard";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("@/lib/home/load-dashboard", () => ({
  loadDashboard: vi.fn(),
}));

const easyWin = {
  strategy_id: "easy_win",
  name: "Easy Win",
  description: "Find useful demand where competition is thin.",
  status: "launch",
  input_shape: "city_service",
} as const;

const gbpBlitz = {
  strategy_id: "gbp_blitz",
  name: "GBP Blitz",
  description: "Prioritize local packs with business profile openings.",
  status: "launch",
  input_shape: "city_service",
} as const;

const keywordHijack = {
  strategy_id: "keyword_hijack",
  name: "Keyword Hijack",
  description: "Target services where organic incumbents are weak.",
  status: "launch",
  input_shape: "city_service_keyword",
} as const;

const cashCow = {
  strategy_id: "cash_cow",
  name: "Cash Cow",
  description: "Deprecated portfolio shortcut.",
  status: "phase_2",
  input_shape: "cached_scan",
} as const;

const readySummary = {
  account_id: "account-1",
  email: "owner@example.com",
  plan_key: "plus",
  plan_label: "Plus",
  monthly_price_cents: 4900,
  monthly_report_limit: 10,
  fresh_reports_used: 2,
  fresh_reports_remaining: 8,
  subscription_status: "active",
  cancel_at_period_end: false,
  current_period_start: "2026-05-01T00:00:00.000Z",
  current_period_end: "2026-06-01T00:00:00.000Z",
  stripe_customer_exists: true,
  billing_management_available: true,
} as const;

function dashboardFixture(overrides: Partial<DashboardData> = {}): DashboardData {
  const base: DashboardData = {
    stats: {
      total_reports: 12,
      avg_score: 71,
      watchlist: 0,
      niches_scored: 12,
    },
    recent: [
      {
        id: "report-123",
        niche: "Roofing",
        city: "Dallas, TX",
        created_at: "2026-05-21T12:00:00.000Z",
      },
    ],
    recommended: [],
    stat_cards: [],
    account: {
      status: "ready",
      error: null,
      summary: readySummary,
      entitlement: {
        account_id: "account-1",
        plan_key: "plus",
        fresh_report_quota_exempt: false,
      },
      can_run_fresh_reports: true,
    },
    onboarding: {
      profile: null,
      target: null,
      starter_strategy_id: "gbp_blitz",
      shortcut_strategy_ids: ["gbp_blitz", "easy_win", "keyword_hijack"],
      next_route: "/strategies",
      error: null,
    },
    strategies: {
      catalog: {
        strategies: [easyWin, gbpBlitz, keywordHijack, cashCow],
        global_modifiers: [],
      },
      starter: gbpBlitz,
      shortcuts: [gbpBlitz, easyWin, keywordHijack],
    },
    report_error: null,
    multi_market_available: true,
  };

  return {
    ...base,
    ...overrides,
    account: overrides.account ?? base.account,
    onboarding: overrides.onboarding ?? base.onboarding,
    strategies: overrides.strategies ?? base.strategies,
    stats: overrides.stats ?? base.stats,
    recent: overrides.recent ?? base.recent,
  };
}

async function renderHome(dashboard: DashboardData) {
  vi.mocked(loadDashboard).mockResolvedValueOnce(dashboard);
  render(await HomePage());
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("HomePage dashboard", () => {
  it("routes paid first-run accounts to the launch-safe starter strategy", async () => {
    await renderHome(
      dashboardFixture({
        recent: [],
        account: {
          status: "ready",
          error: null,
          summary: {
            ...readySummary,
            fresh_reports_used: 0,
            fresh_reports_remaining: 10,
          },
          entitlement: {
            account_id: "account-1",
            plan_key: "plus",
            fresh_report_quota_exempt: false,
          },
          can_run_fresh_reports: true,
        },
      }),
    );

    expect(screen.getByLabelText("Start first dashboard action")).toHaveAttribute(
      "href",
      "/strategies/gbp_blitz",
    );
    expect(screen.getByLabelText("Start first dashboard action")).toHaveTextContent(
      "Open GBP Blitz",
    );
    expect(screen.getByText("Three steps to your first report.")).toBeInTheDocument();
    expect(screen.getByText("Pick your strategy lens")).toBeInTheDocument();
    expect(screen.getByText("Confirm city and service")).toBeInTheDocument();
    expect(screen.getByText("Review the scored report")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Or browse Explore first" })).toHaveAttribute(
      "href",
      "/explore",
    );
  });

  it("routes free first-run accounts to cached Explore and account settings", async () => {
    await renderHome(
      dashboardFixture({
        recent: [],
        account: {
          status: "ready",
          error: null,
          summary: {
            ...readySummary,
            plan_key: "free",
            plan_label: "Free",
            monthly_price_cents: 0,
            monthly_report_limit: 0,
            fresh_reports_used: 0,
            fresh_reports_remaining: 0,
          },
          entitlement: {
            account_id: "account-1",
            plan_key: "free",
            fresh_report_quota_exempt: false,
          },
          can_run_fresh_reports: false,
        },
      }),
    );

    expect(screen.getByLabelText("Start first dashboard action")).toHaveAttribute(
      "href",
      "/explore",
    );
    expect(screen.getByLabelText("Start first dashboard action")).toHaveTextContent(
      "Explore cached reports",
    );
    expect(screen.getAllByRole("link", { name: "Manage plan" }).at(0)).toHaveAttribute(
      "href",
      "/settings",
    );
    expect(screen.queryByRole("link", { name: "Or browse Explore first" })).not.toBeInTheDocument();
  });

  it("renders usage values, recommended CTA, multi-market link, launch shortcuts, and recent report links", async () => {
    await renderHome(dashboardFixture());

    const usage = screen.getByLabelText("Dashboard usage");
    expect(within(usage).getByText("Scans remaining")).toBeInTheDocument();
    expect(within(usage).getByText("8 / 10")).toBeInTheDocument();
    expect(within(usage).getByText("Current plan")).toBeInTheDocument();
    expect(within(usage).getByText("Plus")).toBeInTheDocument();
    expect(within(usage).getByText("Reports")).toBeInTheDocument();
    expect(within(usage).getByText("12")).toBeInTheDocument();
    expect(within(usage).getByText("Current lens")).toBeInTheDocument();
    expect(within(usage).getByText("GBP Blitz")).toBeInTheDocument();
    expect(within(usage).getByRole("link", { name: "Manage" })).toHaveAttribute(
      "href",
      "/settings",
    );
    expect(within(usage).getByRole("link", { name: "View all" })).toHaveAttribute(
      "href",
      "/reports",
    );
    expect(within(usage).getByRole("link", { name: "Change" })).toHaveAttribute(
      "href",
      "/strategies",
    );

    expect(screen.getByText("Recommended for you")).toBeInTheDocument();
    expect(screen.getByLabelText("Open recommended strategy GBP Blitz")).toHaveAttribute(
      "href",
      "/strategies/gbp_blitz",
    );
    expect(screen.getByLabelText("Open recommended strategy GBP Blitz")).toHaveTextContent(
      "Run GBP Blitz",
    );
    expect(screen.getByRole("link", { name: "See all strategies" })).toHaveAttribute(
      "href",
      "/strategies",
    );
    expect(screen.getByRole("link", { name: /Open agency tools/i })).toHaveAttribute(
      "href",
      "/agency",
    );
    expect(screen.getByText("Explore cached data")).toBeInTheDocument();
    expect(screen.getByText("Multi-market scan")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Dallas, TX/i })).toHaveAttribute(
      "href",
      "/reports?open=report-123",
    );
    expect(screen.getByRole("heading", { name: "Your strategy shortcuts" })).toBeInTheDocument();
    expect(screen.getByText("Easy Win")).toBeInTheDocument();
    expect(screen.getByText("Keyword Hijack")).toBeInTheDocument();
    expect(screen.queryByText("Cash Cow")).not.toBeInTheDocument();
  });

  it("shows the disabled multi-market fallback when agency tools are unavailable", async () => {
    await renderHome(dashboardFixture({ multi_market_available: false }));

    expect(screen.queryByRole("link", { name: /Open agency tools/i })).not.toBeInTheDocument();
    expect(screen.getByText("Coming soon")).toHaveAttribute("aria-disabled", "true");
  });

  it("renders an actionable account error state", async () => {
    await renderHome(
      dashboardFixture({
        account: {
          status: "error",
          error: {
            message: "No account is available for this user.",
            code: "account_missing",
            status: 403,
          },
          blocking: true,
          summary: null,
          entitlement: null,
          can_run_fresh_reports: false,
        },
        recent: [],
      }),
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "We could not load your dashboard entitlement.",
    );
    expect(screen.getByRole("link", { name: /Open settings/i })).toHaveAttribute(
      "href",
      "/settings",
    );
    expect(screen.getByRole("link", { name: "Explore cached reports" })).toHaveAttribute(
      "href",
      "/explore",
    );
  });

  it("renders a non-blocking account warning without hiding dashboard content", async () => {
    await renderHome(
      dashboardFixture({
        account: {
          status: "error",
          error: {
            message: "usage counters: relation unavailable",
          },
          blocking: false,
          summary: null,
          entitlement: null,
          can_run_fresh_reports: false,
        },
      }),
    );

    expect(screen.getByLabelText("Account warning")).toHaveTextContent(
      "usage counters: relation unavailable",
    );
    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByText("Recommended for you")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Dallas, TX/i })).toHaveAttribute(
      "href",
      "/reports?open=report-123",
    );
  });

  it("keeps report soft errors visible without blocking the dashboard", async () => {
    await renderHome(
      dashboardFixture({
        report_error: {
          message: "Reports response was invalid JSON.",
        },
      }),
    );

    expect(screen.getByRole("status")).toHaveTextContent(
      "Reports response was invalid JSON.",
    );
    expect(screen.getByText("Recommended for you")).toBeInTheDocument();
  });
});
