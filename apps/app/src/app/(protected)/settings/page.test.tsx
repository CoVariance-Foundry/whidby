// @vitest-environment jsdom
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SettingsPage from "./page";
import { createClient } from "@/lib/supabase/server";
import { resolveEntitlementContext } from "@/lib/account/entitlements";
import { loadAccountSummary } from "@/lib/account/summary";

const mocks = vi.hoisted(() => ({
  sidebar: vi.fn(({ active }: { active: string }) => <aside data-active={active}>Sidebar</aside>),
  topbar: vi.fn(({ crumbs }: { crumbs: string[] }) => <nav>{crumbs.join(" / ")}</nav>),
  client: vi.fn(({ summary }) => <section>Settings for {summary.email}</section>),
}));

vi.mock("@/components/Sidebar", () => ({
  default: mocks.sidebar,
}));

vi.mock("@/components/Topbar", () => ({
  default: mocks.topbar,
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

beforeEach(() => {
  vi.mocked(createClient).mockResolvedValue({} as never);
  vi.mocked(resolveEntitlementContext).mockResolvedValue({
    user: { id: "user-1", email: "owner@example.com" },
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

    expect(screen.getByText("Settings / Account & billing")).toBeInTheDocument();
    expect(screen.getByText("Settings for owner@example.com")).toBeInTheDocument();
    expect(mocks.sidebar).toHaveBeenCalledWith(
      expect.objectContaining({ active: "settings", planLabel: "Plus" }),
      undefined,
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
