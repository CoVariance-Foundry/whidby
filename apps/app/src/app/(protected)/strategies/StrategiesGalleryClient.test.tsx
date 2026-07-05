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
  // @req FR-103
  // @req FR-105
  it("renders the B2 rail with account-aware locks, side branch, and locked Portfolio Builder", () => {
    const catalog = {
      ...FALLBACK_STRATEGY_CATALOG,
      strategies: FALLBACK_STRATEGY_CATALOG.strategies.map((strategy) =>
        strategy.strategy_id === "expand_conquer"
          ? {
              ...strategy,
              description: "Backend copy keeps lookalike expansion markets in the path.",
            }
          : strategy,
      ),
    };
    render(<StrategiesGalleryClient catalog={catalog} />);

    const rail = screen.getByLabelText("B2 strategy path rail");
    expect(within(rail).getByText("Easy Win")).toBeInTheDocument();
    expect(within(rail).getByText("GBP Blitz")).toBeInTheDocument();
    expect(within(rail).getByText("Expand & Conquer")).toBeInTheDocument();

    const easyWinCard = within(rail).getByText("Easy Win").closest("article");
    expect(easyWinCard).not.toBeNull();
    expect(easyWinCard as HTMLElement).toHaveTextContent("Current");
    expect(within(easyWinCard as HTMLElement).getByRole("button", { name: /working here/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    const gbpCard = within(rail).getByText("GBP Blitz").closest("article");
    expect(gbpCard).not.toBeNull();
    expect(gbpCard as HTMLElement).toHaveTextContent("Complete a scan to unlock this step.");

    const expandCard = within(rail).getByText("Expand & Conquer").closest("article");
    expect(expandCard).not.toBeNull();
    expect(expandCard as HTMLElement).toHaveTextContent(
      "Backend copy keeps lookalike expansion markets in the path.",
    );
    expect(expandCard as HTMLElement).toHaveTextContent(
      "Declare a ranked site to unlock this expansion step.",
    );

    const sideBranchSection = screen.getByLabelText("Keyword Hijack side branch");
    expect(within(sideBranchSection).getByText("Keyword Hijack")).toBeInTheDocument();
    const keywordCard = within(sideBranchSection).getByText("Keyword Hijack").closest("article");
    expect(keywordCard).not.toBeNull();
    expect(keywordCard as HTMLElement).toHaveTextContent("Unlock: Feasibility preflight");
    expect(within(keywordCard as HTMLElement).getByRole("button", { name: /work this step/i })).toBeInTheDocument();
    expect(
      within(sideBranchSection).getByRole("button", { name: /what is feasibility/i }),
    ).toBeInTheDocument();

    const lockedSection = screen.getByLabelText("Future path node");
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
    expect(screen.getByLabelText("Inline strategy workbench")).toHaveTextContent("Easy Win");
    expect(screen.queryByText(/cash cow/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/blue ocean/i)).not.toBeInTheDocument();
  });

  it("unlocks the expansion step when the account has a ranked-site declaration", () => {
    render(
      <StrategiesGalleryClient
        catalog={FALLBACK_STRATEGY_CATALOG}
        unlockState={{
          has_completed_scan: true,
          has_ranked_site_declaration: true,
        }}
      />,
    );

    const rail = screen.getByLabelText("B2 strategy path rail");
    const expandCard = within(rail).getByText("Expand & Conquer").closest("article");
    expect(expandCard).not.toBeNull();
    expect(expandCard as HTMLElement).toHaveTextContent("Current");
    expect(within(expandCard as HTMLElement).getByRole("button", { name: /working here/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(expandCard as HTMLElement).not.toHaveTextContent(
      "Declare a ranked site to unlock this expansion step.",
    );
    expect(screen.getByLabelText("Inline strategy workbench")).toHaveTextContent(
      "Expand & Conquer",
    );
  });
});
