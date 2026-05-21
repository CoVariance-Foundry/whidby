// @vitest-environment jsdom
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import AgencyPage from "./page";

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

afterEach(() => {
  cleanup();
});

describe("AgencyPage", () => {
  it("renders the implemented Multi-market destination linked from the app navbar", () => {
    render(<AgencyPage />);

    expect(screen.getByRole("heading", { name: "Multi-market" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Browse markets/i })).toHaveAttribute(
      "href",
      "/explore",
    );
    expect(screen.getByRole("link", { name: /Explore markets/i })).toHaveAttribute(
      "href",
      "/explore",
    );
    expect(screen.getByRole("link", { name: /Strategy lenses/i })).toHaveAttribute(
      "href",
      "/strategies",
    );
    expect(screen.getByRole("link", { name: /Saved reports/i })).toHaveAttribute(
      "href",
      "/reports",
    );
  });
});
