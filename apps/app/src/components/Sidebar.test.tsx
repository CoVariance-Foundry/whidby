// @vitest-environment jsdom
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import Sidebar from "./Sidebar";
import { createClient } from "@/lib/supabase/server";

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

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Sidebar", () => {
  it("adds Explore navigation and preserves Niche finder while marking Explore active", async () => {
    vi.mocked(createClient).mockResolvedValue({
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: {
            user: {
              email: "owner@example.com",
              user_metadata: {},
            },
          },
        }),
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
});
