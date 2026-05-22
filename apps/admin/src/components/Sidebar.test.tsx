// @vitest-environment jsdom
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import Sidebar from "./Sidebar";

vi.mock("next/navigation", () => ({
  usePathname: () => "/billing",
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: { signOut: vi.fn() },
  }),
}));

describe("Sidebar", () => {
  afterEach(() => cleanup());

  it("includes the billing admin navigation link", () => {
    render(<Sidebar />);

    expect(screen.getByTestId("nav-billing")).toHaveAttribute("href", "/billing");
    expect(screen.getByText("Billing")).toBeInTheDocument();
  });
});
