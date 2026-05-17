// @vitest-environment jsdom
import React from "react";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
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

describe("StrategiesGalleryClient", () => {
  it("shows launch strategies and omits cut prototype strategies", () => {
    const catalog: StrategyCatalogResponse = {
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

    render(<StrategiesGalleryClient catalog={catalog} />);

    const launchSection = screen.getByLabelText("Launch strategies");
    expect(within(launchSection).getByText("Easy Win")).toBeInTheDocument();
    expect(within(launchSection).getByText("GBP Blitz")).toBeInTheDocument();
    expect(within(launchSection).getByText("Keyword Hijack")).toBeInTheDocument();
    expect(within(launchSection).getByText("Expand & Conquer")).toBeInTheDocument();
    const expandCard = within(launchSection).getByText("Expand & Conquer").closest("article");
    expect(expandCard).not.toBeNull();
    expect(within(expandCard as HTMLElement).getByRole("link", { name: /open expand & conquer/i })).toHaveClass(
      "btn-primary",
    );
    expect(screen.getByLabelText("Phase 2")).toHaveTextContent("Cash Cow");
    expect(screen.queryByText(/blue ocean/i)).not.toBeInTheDocument();
  });
});
