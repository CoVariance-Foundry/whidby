// @vitest-environment jsdom
import React from "react";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ProtectedLayout from "./layout";
import { createClient } from "@/lib/supabase/server";
import { resolveEntitlementContext } from "@/lib/account/entitlements";
import { loadAccountSummary } from "@/lib/account/summary";

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
  redirect: vi.fn((path: string) => {
    throw new Error(`redirect:${path}`);
  }),
  usePathname: () => "/reports",
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(),
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: { signOut: vi.fn() },
  }),
}));

vi.mock("@/lib/account/entitlements", () => ({
  resolveEntitlementContext: vi.fn(),
}));

vi.mock("@/lib/account/summary", () => ({
  loadAccountSummary: vi.fn(),
}));

beforeEach(() => {
  vi.mocked(createClient).mockResolvedValue({
    auth: {
      getUser: vi.fn().mockResolvedValue({
        data: {
          user: {
            id: "user-1",
            email: "owner@example.com",
            user_metadata: { full_name: "Owner Example" },
          },
        },
      }),
    },
  } as never);
  vi.mocked(resolveEntitlementContext).mockResolvedValue({
    user: { id: "user-1", email: "owner@example.com" },
    entitlement: {
      account_id: "account-1",
      member_role: "owner",
      plan_key: "plus",
      monthly_report_limit: 10,
      subscription_status: "active",
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

describe("ProtectedLayout app frame", () => {
  it("wraps protected pages in the Epic 1 navbar and footer using account usage", async () => {
    render(
      await ProtectedLayout({
        children: <section>Protected child</section>,
      }),
    );

    const primaryNav = screen.getByRole("navigation", { name: "Primary navigation" });
    expect(primaryNav).toBeInTheDocument();
    expect(within(primaryNav).getByRole("link", { name: "Reports" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByLabelText("Plan usage")).toHaveTextContent("4/10 scans");
    expect(screen.getByText("Protected child")).toBeInTheDocument();
    expect(screen.getByRole("contentinfo", { name: "Product footer" })).toBeInTheDocument();
  });

  it("keeps the frame usable when entitlement summary loading fails", async () => {
    vi.mocked(resolveEntitlementContext).mockRejectedValueOnce(new Error("account unavailable"));

    render(
      await ProtectedLayout({
        children: <section>Fallback child</section>,
      }),
    );

    expect(screen.getByLabelText("Plan usage")).toHaveTextContent("0/0 scans");
    expect(screen.getByLabelText("Plan usage")).toHaveTextContent("Free");
    expect(screen.getByText("Fallback child")).toBeInTheDocument();
  });
});
