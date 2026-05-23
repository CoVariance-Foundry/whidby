// @vitest-environment jsdom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AccountSettingsClient from "./AccountSettingsClient";
import { createClient } from "@/lib/supabase/client";
import type { AccountSummary } from "@/lib/account/summary";
import type { ProfileSummary, SavedReportPreview } from "./AccountSettingsClient";

const mocks = vi.hoisted(() => ({
  searchParams: "",
  resetPasswordForEmail: vi.fn(),
  signOut: vi.fn(),
  routerPush: vi.fn(),
}));

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

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(mocks.searchParams),
  useRouter: () => ({
    push: mocks.routerPush,
  }),
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: vi.fn(),
}));

const baseSummary: AccountSummary = {
  account_id: "account-1",
  email: "owner@example.com",
  plan_key: "free",
  plan_label: "Free",
  monthly_price_cents: 0,
  monthly_report_limit: 0,
  fresh_reports_used: 0,
  fresh_reports_remaining: 0,
  subscription_status: "active",
  cancel_at_period_end: false,
  current_period_start: "2026-05-01T00:00:00.000Z",
  current_period_end: "2026-06-01T00:00:00.000Z",
  stripe_customer_exists: false,
  billing_management_available: true,
};

function renderClient({
  summary,
  profile,
  savedReports,
  savedReportsError,
}: {
  summary?: Partial<AccountSummary>;
  profile?: ProfileSummary | null;
  savedReports?: SavedReportPreview[];
  savedReportsError?: string | null;
} = {}) {
  return render(
    <AccountSettingsClient
      summary={{ ...baseSummary, ...summary }}
      profile={profile}
      savedReports={savedReports}
      savedReportsError={savedReportsError}
    />,
  );
}

beforeEach(() => {
  mocks.searchParams = "";
  mocks.resetPasswordForEmail.mockResolvedValue({ error: null });
  mocks.signOut.mockResolvedValue({ error: null });
  vi.mocked(createClient).mockReturnValue({
    auth: {
      resetPasswordForEmail: mocks.resetPasswordForEmail,
      signOut: mocks.signOut,
    },
  } as never);
  global.fetch = vi.fn();
  Object.defineProperty(window, "location", {
    value: {
      origin: "http://localhost:3002",
      assign: vi.fn(),
    },
    writable: true,
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("AccountSettingsClient", () => {
  it("renders Free users with cached access and upgrade CTAs", () => {
    renderClient();

    expect(screen.getAllByRole("heading", { name: "Free" }).length).toBeGreaterThan(0);
    expect(screen.getByText(/cached market intelligence is available/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Reports used 0 of 0")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /upgrade to plus/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /upgrade to pro/i })).toBeInTheDocument();
    expect(screen.getAllByText("owner@example.com").length).toBeGreaterThanOrEqual(1);
  });

  it("renders Supabase profile metadata when available", () => {
    renderClient({
      profile: {
        email: "owner@example.com",
        name: "Antwoine Flowers",
        segment: "Agency owner",
        referred_by: "Coach Maya",
      },
    });

    expect(screen.getByText("Antwoine Flowers")).toBeInTheDocument();
    expect(screen.getByText("Agency owner")).toBeInTheDocument();
    expect(screen.getByText("Coach Maya")).toBeInTheDocument();
    expect(screen.queryByText("undefined")).not.toBeInTheDocument();
  });

  it("renders Plus usage with remaining reports and reset date", () => {
    renderClient({
      summary: {
        plan_key: "plus",
        plan_label: "Plus",
        monthly_price_cents: 4900,
        monthly_report_limit: 10,
        fresh_reports_used: 4,
        fresh_reports_remaining: 6,
        stripe_customer_exists: true,
      },
    });

    expect(screen.getAllByRole("heading", { name: "Plus" }).length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Reports used 4 of 10")).toBeInTheDocument();
    expect(screen.getByText(/6 fresh reports remain/i)).toBeInTheDocument();
    expect(screen.getAllByText(/June 1, 2026/i).length).toBeGreaterThan(0);
  });

  it("shows an exhausted quota warning", () => {
    renderClient({
      summary: {
        plan_key: "plus",
        plan_label: "Plus",
        monthly_price_cents: 4900,
        monthly_report_limit: 10,
        fresh_reports_used: 10,
        fresh_reports_remaining: 0,
        stripe_customer_exists: true,
      },
    });

    expect(screen.getByText(/fresh reports are exhausted/i)).toBeInTheDocument();
  });

  it("shows scheduled cancellation state for paid subscriptions", () => {
    renderClient({
      summary: {
        plan_key: "plus",
        plan_label: "Plus",
        monthly_price_cents: 4900,
        monthly_report_limit: 10,
        fresh_reports_used: 4,
        fresh_reports_remaining: 6,
        stripe_customer_exists: true,
        cancel_at_period_end: true,
      },
    });

    expect(screen.getByText(/cancels at period end/i)).toBeInTheDocument();
    expect(screen.getByText("Subscription scheduled to cancel")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /manage in stripe/i })).toBeInTheDocument();
  });

  it("does not call Stripe when billing is disabled", () => {
    renderClient({ summary: { billing_management_available: false } });

    const plusButton = screen.getByRole("button", { name: /upgrade to plus/i });
    expect(plusButton).toBeDisabled();
    fireEvent.click(plusButton);

    expect(vi.mocked(global.fetch)).not.toHaveBeenCalledWith(
      "/api/billing/checkout",
      expect.anything(),
    );
  });

  it("renders a server-loaded saved reports preview", () => {
    renderClient({
      savedReports: [
        {
          id: "report-1",
          niche: "Plumbing",
          city: "Austin, TX",
          archetype_short: "Easy win",
          opportunity_score: 82,
          created_at: "2026-05-20T00:00:00.000Z",
        },
      ],
    });

    expect(screen.getByRole("heading", { name: "Saved reports" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /plumbing · austin/i })).toHaveAttribute(
      "href",
      "/reports?open=report-1",
    );
    expect(screen.getByText(/82 opportunity/i)).toBeInTheDocument();
  });

  it("shows the empty saved reports state", () => {
    renderClient();

    expect(screen.getByText("No saved reports yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Explore markets" })).toHaveAttribute(
      "href",
      "/explore",
    );
  });

  it("shows the saved reports fallback when server loading fails", () => {
    renderClient({ savedReportsError: "Reports request failed with HTTP 502." });

    expect(screen.getByText("Reports could not load")).toBeInTheDocument();
    expect(screen.getByText(/HTTP 502/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open reports" })).toHaveAttribute("href", "/reports");
  });

  it("renders a billing return banner from query params", () => {
    mocks.searchParams = "billing=success";
    renderClient();
    expect(screen.getByRole("status")).toHaveTextContent("Billing details refreshed.");
  });

  it("renders a cancelled billing return banner from query params", () => {
    mocks.searchParams = "billing=cancelled";
    renderClient();
    expect(screen.getByRole("status")).toHaveTextContent("Billing change cancelled.");
  });

  it("renders a password return banner from query params", () => {
    mocks.searchParams = "password=updated";
    renderClient();
    expect(screen.getByRole("status")).toHaveTextContent("Password updated.");
  });

  it("sends a password reset email with the settings password redirect", async () => {
    renderClient();

    expect(screen.getByRole("link", { name: "Manage password" })).toHaveAttribute(
      "href",
      "/settings/password",
    );
    fireEvent.click(screen.getByRole("button", { name: /send reset email/i }));

    await waitFor(() => {
      expect(mocks.resetPasswordForEmail).toHaveBeenCalledWith("owner@example.com", {
        redirectTo: "http://localhost:3002/auth/callback?next=/settings/password",
      });
    });
    expect(screen.getByRole("status")).toHaveTextContent("Password reset email sent.");
  });

  it("signs out through Supabase and returns to login", async () => {
    renderClient();

    fireEvent.click(screen.getByRole("button", { name: /^sign out$/i }));

    await waitFor(() => expect(mocks.signOut).toHaveBeenCalledTimes(1));
    expect(mocks.routerPush).toHaveBeenCalledWith("/login");
  });
});
