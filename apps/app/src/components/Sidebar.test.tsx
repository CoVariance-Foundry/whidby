// @vitest-environment jsdom
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import Sidebar from "./Sidebar";
import { createClient } from "@/lib/supabase/server";
import { resolveEntitlementContext } from "@/lib/account/entitlements";

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
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(),
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: {
      signOut: vi.fn(),
    },
  }),
}));

vi.mock("@/lib/account/entitlements", () => ({
  resolveEntitlementContext: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Sidebar", () => {
  function mockSupabaseUser(email = "owner@example.com") {
    vi.mocked(createClient).mockResolvedValue({
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: {
            user: {
              email,
              user_metadata: {},
            },
          },
        }),
      },
    } as never);
  }

  it("adds Explore navigation and preserves Niche finder while marking Explore active", async () => {
    mockSupabaseUser();
    vi.mocked(resolveEntitlementContext).mockResolvedValue({
      user: { id: "user-1", email: "owner@example.com" },
      entitlement: {
        account_id: "account-1",
        member_role: "owner",
        plan_key: "free",
        monthly_report_limit: 0,
        subscription_status: "active",
        current_period_start: "2026-05-01T00:00:00.000Z",
        current_period_end: "2026-06-01T00:00:00.000Z",
      },
    } as never);

    render(await Sidebar({ active: "explore" }));

    const explore = screen.getByRole("link", { name: /explore/i });
    const finder = screen.getByRole("link", { name: /niche finder/i });

    expect(explore.getAttribute("href")).toBe("/explore");
    expect(explore.getAttribute("aria-current")).toBe("page");
    expect(explore.classList.contains("sidebar-item")).toBe(true);
    expect(explore.classList.contains("active")).toBe(true);
    expect(finder.getAttribute("href")).toBe("/niche-finder");
    expect(finder.getAttribute("aria-current")).toBeNull();
    expect(finder.classList.contains("sidebar-item")).toBe(true);
    expect(finder.classList.contains("active")).toBe(false);
  });

  it("shows the user email, live plan label, and settings menu active state", async () => {
    mockSupabaseUser("owner@example.com");
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

    render(await Sidebar({ active: "settings" }));

    expect(screen.getByText("owner@example.com")).toBeInTheDocument();
    expect(screen.getByText("Plus plan")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /owner@example.com/i }));
    const account = screen.getByRole("menuitem", { name: /account settings/i });
    expect(account.getAttribute("href")).toBe("/settings");
    expect(account).toHaveStyle({ background: "var(--accent-soft)" });
  });

  it("uses a supplied plan label without resolving entitlement again", async () => {
    mockSupabaseUser("owner@example.com");

    render(await Sidebar({ active: "settings", planLabel: "Pro" }));

    expect(resolveEntitlementContext).not.toHaveBeenCalled();
    expect(screen.getByText("Pro plan")).toBeInTheDocument();
  });
});
