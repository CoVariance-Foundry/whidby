// @vitest-environment jsdom
import React from "react";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { resolveStrategyRecommendation } from "@/lib/strategies/recommendation";
import type { StrategyCatalogResponse } from "@/lib/strategies/types";
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

function makeCatalog(): StrategyCatalogResponse {
  return {
    strategies: [
      {
        strategy_id: "easy_win",
        name: "Easy Win",
        description: "Weak competition markets.",
        status: "launch",
        input_shape: "city_service",
      },
      {
        strategy_id: "gbp_blitz",
        name: "GBP Blitz",
        description: "Profile-gap markets.",
        status: "launch",
        input_shape: "city_service",
      },
      {
        strategy_id: "keyword_hijack",
        name: "Keyword Hijack",
        description: "Keyword-led markets.",
        status: "launch",
        input_shape: "city_service_keyword",
      },
      {
        strategy_id: "expand_conquer",
        name: "Expand & Conquer",
        description: "Reference-market expansion.",
        status: "launch",
        input_shape: "reference_city_service",
      },
      {
        strategy_id: "cash_cow",
        name: "Cash Cow",
        description: "Phase-2 economics lens.",
        status: "phase_2",
        input_shape: "cached_scan",
      },
    ],
    global_modifiers: [],
  };
}

describe("StrategiesGalleryClient", () => {
  it("shows launch strategies as available and keeps phase 2 strategies locked", () => {
    const catalog = makeCatalog();

    render(<StrategiesGalleryClient catalog={catalog} />);

    expect(screen.getByRole("heading", { name: "Pick a lens." })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /browse explore first/i })).toHaveAttribute("href", "/explore");

    const availableSection = screen.getByLabelText("Available to you");
    expect(within(availableSection).getByText("Easy Win")).toBeInTheDocument();
    expect(within(availableSection).getByText("GBP Blitz")).toBeInTheDocument();
    expect(within(availableSection).getByText("Keyword Hijack")).toBeInTheDocument();
    expect(within(availableSection).getByText("Expand & Conquer")).toBeInTheDocument();
    const expandCard = within(availableSection).getByText("Expand & Conquer").closest("article");
    expect(expandCard).not.toBeNull();
    expect(screen.getByRole("link", { name: /open expand & conquer/i })).toHaveAttribute(
      "href",
      "/strategies/expand_conquer",
    );

    const lockedSection = screen.getByLabelText("Unlock as you progress");
    expect(lockedSection).toHaveTextContent("Cash Cow");
    expect(screen.queryByText(/blue ocean/i)).not.toBeInTheDocument();
  });

  it("filters to AI-proof strategies and shows the toggle state", () => {
    render(<StrategiesGalleryClient catalog={makeCatalog()} />);

    const toggle = screen.getByRole("button", { name: /ai-proof filter off/i });
    expect(toggle).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByText("Expand & Conquer")).toBeInTheDocument();

    fireEvent.click(toggle);

    expect(screen.getByRole("button", { name: /ai-proof filter on/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByText("Easy Win")).toBeInTheDocument();
    expect(screen.getByText("GBP Blitz")).toBeInTheDocument();
    expect(screen.queryByText("Keyword Hijack")).not.toBeInTheDocument();
    expect(screen.queryByText("Expand & Conquer")).not.toBeInTheDocument();
  });

  it("shows the recommendation banner and marks the recommended strategy", () => {
    render(
      <StrategiesGalleryClient
        catalog={makeCatalog()}
        recommendedStrategyId="gbp_blitz"
        recommendationReason="your first target depends on local profile gaps"
      />,
    );

    expect(screen.getByLabelText("Strategy recommendation")).toHaveTextContent("Our recommendation");
    expect(screen.getByText(/your first target depends on local profile gaps/i)).toBeInTheDocument();

    const recommendedCard = screen.getByRole("link", { name: /open gbp blitz/i }).querySelector("article");
    expect(recommendedCard).not.toBeNull();
    expect(within(recommendedCard as HTMLElement).getByText("Recommended")).toBeInTheDocument();
  });

  it("renders phase 2 cards as locked and non-clickable", () => {
    render(<StrategiesGalleryClient catalog={makeCatalog()} />);

    const cashCowCard = screen.getByText("Cash Cow").closest("article");
    expect(cashCowCard).not.toBeNull();
    expect(within(cashCowCard as HTMLElement).getByText("Locked")).toBeInTheDocument();
    expect(within(cashCowCard as HTMLElement).queryByText("Unlocked")).not.toBeInTheDocument();
    expect(within(cashCowCard as HTMLElement).queryByRole("link")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /open cash cow/i })).not.toBeInTheDocument();
  });
});

describe("resolveStrategyRecommendation", () => {
  it("keeps launch-safe profile recommendations", () => {
    expect(
      resolveStrategyRecommendation({
        profile: { recommended_strategy_id: "gbp_blitz" },
        target: { strategy_id: "easy_win" },
      }),
    ).toBe("gbp_blitz");
  });

  it("falls back to target strategy when profile recommendation is missing", () => {
    expect(
      resolveStrategyRecommendation({
        profile: { recommended_strategy_id: null },
        target: { strategy_id: "expand_conquer" },
      }),
    ).toBe("expand_conquer");
  });

  it("normalizes deprecated or phase 2 strategy ids to easy_win", () => {
    expect(
      resolveStrategyRecommendation({
        profile: { recommended_strategy_id: "cash_cow" },
        target: { strategy_id: "gbp_blitz" },
      }),
    ).toBe("easy_win");
  });

  it("omits recommendation when no onboarding route data exists", () => {
    expect(resolveStrategyRecommendation({ profile: null, target: null })).toBeUndefined();
  });
});
