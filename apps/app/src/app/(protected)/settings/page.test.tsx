// @vitest-environment jsdom
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SettingsPage from "./page";
import { createClient } from "@/lib/supabase/server";
import { resolveEntitlementContext } from "@/lib/account/entitlements";
import { loadAccountSummary } from "@/lib/account/summary";

const mocks = vi.hoisted(() => ({
  client: vi.fn(({ summary }) => <section>Settings for {summary.email}</section>),
  headersGet: vi.fn(),
}));

vi.mock("./AccountSettingsClient", () => ({
  default: mocks.client,
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(),
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
    resolveEntitlementContext: vi.fn(),
  };
});

vi.mock("@/lib/account/summary", () => ({
  loadAccountSummary: vi.fn(),
}));

vi.mock("next/headers", () => ({
  headers: vi.fn(async () => ({
    get: mocks.headersGet,
  })),
}));

beforeEach(() => {
  delete process.env.WIDBY_APP_BASE_URL;
  delete process.env.NEXT_PUBLIC_APP_URL;
  delete process.env.NEXT_PUBLIC_SITE_URL;
  delete process.env.VERCEL_URL;
  mocks.headersGet.mockImplementation((name: string) => {
    const values: Record<string, string> = {
      "x-forwarded-host": "preview.whidby.test",
      "x-forwarded-proto": "https",
      cookie: "sb-access-token=abc",
    };
    return values[name] ?? null;
  });
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      status: "success",
      reports: [
        {
          id: "report-1",
          niche: "Plumbing",
          city: "Austin, TX",
          archetype_short: "Easy win",
          opportunity_score: 82,
          created_at: "2026-05-20T00:00:00.000Z",
        },
      ],
    }),
  });
  vi.mocked(createClient).mockResolvedValue({} as never);
  vi.mocked(resolveEntitlementContext).mockResolvedValue({
    user: {
      id: "user-1",
      email: "owner@example.com",
      user_metadata: {
        name: "Owner Example",
        segment: "Agency",
        coach_ref: "Coach A",
      },
    },
    entitlement: {
      account_id: "account-1",
      member_role: "owner",
      plan_key: "plus",
      monthly_report_limit: 10,
      subscription_status: "active",
      cancel_at_period_end: false,
      current_period_start: "2026-05-01T00:00:00.000Z",
      current_period_end: "2026-06-01T00:00:00.000Z",
    },
  } as never);
  vi.mocked(loadAccountSummary).mockResolvedValue({
    account_id: "account-1",
    email: "owner@example.com",
    plan_key: "plus",
    plan_label: "Plus",
    monthly_price_cents: 4900,
    monthly_report_limit: 10,
    fresh_reports_used: 4,
    fresh_reports_remaining: 6,
    subscription_status: "active",
    cancel_at_period_end: false,
    current_period_start: "2026-05-01T00:00:00.000Z",
    current_period_end: "2026-06-01T00:00:00.000Z",
    stripe_customer_exists: true,
    billing_management_available: true,
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("SettingsPage", () => {
  it("loads account summary and renders the settings surface", async () => {
    render(await SettingsPage());

    expect(screen.getByRole("heading", { name: "Account & billing" })).toBeInTheDocument();
    expect(screen.getByText("Settings for owner@example.com")).toBeInTheDocument();
    expect(mocks.client).toHaveBeenCalledWith(
      expect.objectContaining({
        profile: {
          email: "owner@example.com",
          name: "Owner Example",
          segment: "Agency",
          referred_by: "Coach A",
        },
        savedReports: [
          expect.objectContaining({
            id: "report-1",
            niche: "Plumbing",
          }),
        ],
        savedReportsError: null,
      }),
      undefined,
    );
  });

  it("does not forward cookies when the reports URL comes from request host headers", async () => {
    render(await SettingsPage());

    expect(global.fetch).toHaveBeenCalledWith(
      "https://preview.whidby.test/api/agent/reports?limit=5",
      { cache: "no-store" },
    );
  });

  it("forwards cookies only when the reports URL comes from a configured base URL", async () => {
    process.env.WIDBY_APP_BASE_URL = "https://app.whidby.test";

    render(await SettingsPage());

    expect(global.fetch).toHaveBeenCalledWith(
      "https://app.whidby.test/api/agent/reports?limit=5",
      {
        cache: "no-store",
        headers: { cookie: "sb-access-token=abc" },
      },
    );
  });

  it("renders an account unavailable state when entitlement resolution fails", async () => {
    vi.mocked(resolveEntitlementContext).mockRejectedValueOnce(
      new Error("No account is available for this user."),
    );

    render(await SettingsPage());

    expect(screen.getByRole("alert")).toHaveTextContent("We could not load billing details.");
  });
});
