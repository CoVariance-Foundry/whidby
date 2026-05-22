// @vitest-environment jsdom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import Navbar, { type NavbarUser } from "./Navbar";
import { createClient } from "@/lib/supabase/client";

const routerPush = vi.fn();
let pathname = "/";

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
  usePathname: () => pathname,
  useRouter: () => ({
    push: routerPush,
  }),
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: vi.fn(),
}));

const user: NavbarUser = {
  email: "owner@example.com",
  displayName: "Owner Example",
  initials: "OE",
  planLabel: "Plus",
  scansUsed: 4,
  scansLimit: 10,
  adminUrl: "https://admin.example.com",
  isAdmin: true,
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  pathname = "/";
});

describe("Navbar", () => {
  it("renders the Epic 1 authenticated nav with usage and without deprecated primary items", () => {
    pathname = "/explore";

    render(<Navbar user={user} />);

    const explore = screen.getByRole("link", { name: "Explore" });

    expect(explore.getAttribute("href")).toBe("/explore");
    expect(explore.getAttribute("aria-current")).toBe("page");
    expect(screen.getByRole("link", { name: "Strategies" }).getAttribute("href")).toBe(
      "/strategies",
    );
    expect(screen.getByRole("link", { name: "Multi-market" }).getAttribute("href")).toBe(
      "/agency",
    );
    expect(screen.queryByRole("link", { name: /niche finder/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /recommendations/i })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Plan usage")).toHaveTextContent("4/10 scans");
    expect(screen.getByLabelText("Plan usage")).toHaveTextContent("Plus");
  });

  it("opens the profile menu and preserves settings, admin, password, and sign-out actions for admins", async () => {
    const signOut = vi.fn().mockResolvedValue({ error: null });
    vi.mocked(createClient).mockReturnValue({
      auth: { signOut },
    } as never);

    render(<Navbar user={user} />);

    fireEvent.click(screen.getByRole("button", { name: /open account menu/i }));

    expect(screen.getByRole("menuitem", { name: "Account settings" })).toHaveAttribute(
      "href",
      "/settings",
    );
    expect(screen.getByRole("menuitem", { name: "Password" })).toHaveAttribute(
      "href",
      "/settings/password",
    );
    expect(screen.getByRole("menuitem", { name: "Admin dashboard" })).toHaveAttribute(
      "href",
      "https://admin.example.com",
    );
    expect(screen.getByRole("menuitem", { name: "Admin dashboard" })).toHaveAttribute(
      "target",
      "_blank",
    );
    expect(screen.getByRole("menuitem", { name: "Admin dashboard" })).toHaveAttribute(
      "rel",
      "noreferrer",
    );

    fireEvent.click(screen.getByRole("menuitem", { name: "Sign out" }));

    await waitFor(() => expect(signOut).toHaveBeenCalledTimes(1));
    expect(routerPush).toHaveBeenCalledWith("/login");
  });

  it("hides the admin dashboard action for non-admin users", () => {
    render(<Navbar user={{ ...user, isAdmin: false }} />);

    fireEvent.click(screen.getByRole("button", { name: /open account menu/i }));

    expect(screen.getByRole("menuitem", { name: "Account settings" })).toHaveAttribute(
      "href",
      "/settings",
    );
    expect(screen.getByRole("menuitem", { name: "Password" })).toHaveAttribute(
      "href",
      "/settings/password",
    );
    expect(screen.queryByRole("menuitem", { name: "Admin dashboard" })).not.toBeInTheDocument();
  });

  it("keeps sign-out available when Supabase sign-out fails", async () => {
    const signOut = vi.fn().mockRejectedValue(new Error("network unavailable"));
    vi.mocked(createClient).mockReturnValue({
      auth: { signOut },
    } as never);

    render(<Navbar user={user} />);

    fireEvent.click(screen.getByRole("button", { name: /open account menu/i }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Sign out" }));

    await waitFor(() => expect(signOut).toHaveBeenCalledTimes(1));
    await waitFor(() =>
      expect(screen.getByRole("menuitem", { name: "Sign out" })).not.toBeDisabled(),
    );
    expect(routerPush).not.toHaveBeenCalled();
  });

  it("suppresses primary navigation during onboarding routes", () => {
    pathname = "/onboarding";

    render(<Navbar user={user} />);

    expect(screen.getByRole("link", { name: "Back to home" })).toHaveAttribute("href", "/");
    expect(screen.queryByRole("link", { name: "Explore" })).not.toBeInTheDocument();
  });
});
