// @vitest-environment jsdom
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import NextMoveCard from "./NextMoveCard";

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

describe("NextMoveCard", () => {
  it("renders the title, subtitle, default CTA, and href", () => {
    render(<NextMoveCard href="/reports" title="Review top report" subtitle="Open the strongest cached market." />);

    expect(screen.getByText("Review top report")).toBeInTheDocument();
    expect(screen.getByText("Open the strongest cached market.")).toBeInTheDocument();
    expect(screen.getByText("Continue")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Continue: Review top report" })).toHaveAttribute("href", "/reports");
  });

  it("renders custom CTA text and primary state", () => {
    render(
      <NextMoveCard
        href="/explore"
        title="Compare metros"
        subtitle="Scan city-service gaps."
        ctaLabel="Open Explore"
        primary
      />,
    );

    const link = screen.getByRole("link", { name: "Open Explore: Compare metros" });
    expect(link).toHaveAttribute("href", "/explore");
    expect(link).toHaveAttribute("data-primary", "true");
    expect(screen.getByText("Open Explore")).toBeInTheDocument();
  });
});
