// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { FullReportData } from "@/lib/niche-finder/types";
import ReportDetailModal from "./ReportDetailModal";

afterEach(() => {
  cleanup();
  document.body.innerHTML = "";
});

const report: FullReportData = {
  id: "report-1",
  created_at: "2026-05-20T12:00:00.000Z",
  spec_version: "1.0",
  niche_keyword: "garage door repair",
  geo_scope: "metro",
  geo_target: "New York, NY",
  report_depth: "standard",
  strategy_profile: "launch",
  resolved_weights: null,
  keyword_expansion: null,
  meta: null,
  metros: [
    {
      cbsa_code: "35620",
      cbsa_name: "New York",
      population: 19_000_000,
      serp_archetype: "LOCAL_PACK",
      scores: {
        demand: 82,
        organic_competition: 65,
        local_competition: 70,
        monetization: 76,
        ai_resilience: 81,
        opportunity: 84,
        confidence: { score: 90 },
      },
      guidance: {
        summary: "Lead with borough-specific landing pages.",
        action_items: ["Build city/service pages first.", "Prioritize review-gap competitors."],
      },
    },
  ],
};

describe("ReportDetailModal", () => {
  it("renders strategy guidance from existing metro data and report Next Moves", () => {
    render(<ReportDetailModal report={report} onClose={vi.fn()} />);

    expect(screen.getByText("Strategy guidance")).toBeInTheDocument();
    expect(screen.getByText("Lead with borough-specific landing pages.")).toBeInTheDocument();
    expect(screen.getByText("Priority actions")).toBeInTheDocument();
    expect(screen.getByText("00")).toBeInTheDocument();
    expect(screen.getByText("Build city/service pages first.")).toBeInTheDocument();
    expect(screen.getByText("01")).toBeInTheDocument();
    expect(screen.getByText("Prioritize review-gap competitors.")).toBeInTheDocument();

    expect(screen.getByRole("link", { name: /browse similar markets/i })).toHaveAttribute(
      "href",
      "/explore?city=New%20York&service=garage%20door%20repair",
    );
    expect(screen.getByRole("link", { name: /check the economics/i })).toHaveAttribute(
      "href",
      "/strategies/cash_cow",
    );
    expect(screen.getByRole("link", { name: /find lookalike cities/i })).toHaveAttribute(
      "href",
      "/strategies/expand_conquer",
    );
  });
});
