// @vitest-environment jsdom
import React from "react";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FALLBACK_STRATEGY_CATALOG } from "@/lib/strategies/catalog";
import StrategiesGalleryClient from "./StrategiesGalleryClient";

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

describe("StrategiesGalleryClient", () => {
  it("shows path steps, side branch, and locked Portfolio Builder while omitting deferred plays", () => {
    render(<StrategiesGalleryClient catalog={FALLBACK_STRATEGY_CATALOG} />);

    const pathSection = screen.getByLabelText("Path steps");
    expect(within(pathSection).getByText("Easy Win")).toBeInTheDocument();
    expect(within(pathSection).getByText("GBP Blitz")).toBeInTheDocument();
    expect(within(pathSection).getByText("Expand & Conquer")).toBeInTheDocument();
    const expandCard = within(pathSection).getByText("Expand & Conquer").closest("article");
    expect(expandCard).not.toBeNull();
    expect(within(expandCard as HTMLElement).getByRole("link", { name: /open expand & conquer/i })).toHaveClass(
      "btn-primary",
    );
    const sideBranchSection = screen.getByLabelText("Side branch");
    expect(within(sideBranchSection).getByText("Keyword Hijack")).toBeInTheDocument();
    const keywordCard = within(sideBranchSection).getByText("Keyword Hijack").closest("article");
    expect(keywordCard).not.toBeNull();
    expect(keywordCard as HTMLElement).toHaveTextContent("Unlock: Feasibility preflight");
    expect(
      within(sideBranchSection).getByRole("button", { name: /what is feasibility/i }),
    ).toBeInTheDocument();

    const lockedSection = screen.getByLabelText("Locked node");
    expect(within(lockedSection).getByText("Portfolio Builder")).toBeInTheDocument();
    expect(
      within(lockedSection).getByRole("button", { name: /what is portfolio builder/i }),
    ).toBeInTheDocument();
    expect(within(lockedSection).getByLabelText("Portfolio Builder is locked")).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    expect(screen.getByRole("button", { name: /what is ai resilience/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /what is lookalike/i })).toBeInTheDocument();
    expect(screen.queryByText(/cash cow/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/blue ocean/i)).not.toBeInTheDocument();
  });
});
