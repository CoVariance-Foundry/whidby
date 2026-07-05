// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import type { AnchorHTMLAttributes } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ReportV11Detail from "./ReportV11Detail";
import type { FullReportData } from "@/lib/niche-finder/types";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...props
  }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

const report: FullReportData = {
  id: "rpt_123",
  created_at: "2026-05-22T12:00:00Z",
  spec_version: "1.1",
  niche_keyword: "plumber",
  geo_scope: "metro",
  geo_target: "Phoenix, AZ",
  report_depth: "standard",
  strategy_profile: "easy_win",
  resolved_weights: null,
  keyword_expansion: null,
  metros: [
    {
      cbsa_code: "38060",
      cbsa_name: "Phoenix-Mesa-Chandler, AZ",
      population: 4968450,
      serp_archetype: "PACK_VULN",
      difficulty_tier: "MODERATE",
      ai_exposure: "AI_MINIMAL",
      scores: {
        demand: 72,
        organic_competition: 65,
        local_competition: 58,
        monetization: 80,
        ai_resilience: 85,
        opportunity: 74,
        confidence: { score: 90 },
      },
      signals: {
        demand: {
          total_search_volume: 4200,
          avg_cpc: 12.5,
        },
        organic_competition: {
          avg_top5_da: 32,
        },
        local_competition: {
          review_velocity_avg: 3.5,
        },
        monetization: {
          business_density: 45,
        },
        ai_resilience: {
          aio_trigger_rate: 0.05,
        },
      },
      guidance: {
        summary: "Strong local service opportunity.",
        action_items: ["Audit the top three operators."],
      },
    },
  ],
  meta: null,
};

afterEach(cleanup);

describe("ReportV11Detail", () => {
  it("renders the V1.1 score, signals, evidence, AI Resilience, confidence, and next steps sections", () => {
    render(<ReportV11Detail report={report} />);

    expect(screen.getByRole("heading", { name: "plumber" })).toBeInTheDocument();
    expect(screen.getAllByText("Easy Win").length).toBeGreaterThan(0);
    expect(screen.getByRole("region", { name: /score and verdict/i })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /signal scores/i })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /score breakdown/i })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /evidence/i })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /next steps/i })).toBeInTheDocument();
    expect(screen.getAllByText("AI Resilience").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Confidence: 90").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Strong local service opportunity.").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /run competitor intel/i })).toHaveAttribute(
      "href",
      expect.stringContaining("report_id=rpt_123"),
    );
  });

  it("degrades gracefully when optional fields are missing and does not expose BALANCED", () => {
    const { container } = render(
      <ReportV11Detail
        report={{
          ...report,
          strategy_profile: "BALANCED",
          metros: [
            {
              ...report.metros[0],
              serp_archetype: undefined,
              difficulty_tier: undefined,
              ai_exposure: undefined,
              scores: {
                ...report.metros[0].scores,
                confidence: undefined,
              },
              signals: undefined,
              guidance: undefined,
            },
          ],
        }}
      />,
    );

    expect(screen.getAllByText("Standard scoring").length).toBeGreaterThan(0);
    expect(container).not.toHaveTextContent(/balanced/i);
    expect(screen.getByText("Confidence: Not scored yet")).toBeInTheDocument();
    expect(screen.getByText("Signal-level evidence is not available for this report yet.")).toBeInTheDocument();
    expect(screen.getByText("No narrative evidence is available for this report yet.")).toBeInTheDocument();
  });

  it("renders nested generated M8 guidance in the summary and evidence sections", () => {
    render(
      <ReportV11Detail
        report={{
          ...report,
          metros: [
            {
              ...report.metros[0],
              guidance: {
                guidance: {
                  headline: "Phoenix has a fast local-pack opening.",
                  strategy: "Launch a proof-led city page before the pack gets more expensive.",
                  priority_actions: [
                    "Refresh GBP proof for the highest-converting service line.",
                    "Map review gaps against the top three operators.",
                  ],
                  ai_resilience_note: "AI overviews are unlikely to absorb urgent plumbing demand.",
                  guidance_status: "generated",
                },
              },
            },
          ],
        }}
      />,
    );

    expect(screen.queryByText("No additional evidence is available for this result.")).not.toBeInTheDocument();
    expect(screen.queryByText("No narrative evidence is available for this report yet.")).not.toBeInTheDocument();
    expect(screen.getAllByText("Phoenix has a fast local-pack opening.").length).toBeGreaterThanOrEqual(2);
    expect(
      screen.getAllByText("Launch a proof-led city page before the pack gets more expensive.").length,
    ).toBeGreaterThanOrEqual(2);
    expect(
      screen.getAllByText("AI overviews are unlikely to absorb urgent plumbing demand.").length,
    ).toBeGreaterThanOrEqual(2);
    expect(
      screen.getAllByText("Refresh GBP proof for the highest-converting service line.").length,
    ).toBeGreaterThanOrEqual(2);
    expect(
      screen.getAllByText("Map review gaps against the top three operators.").length,
    ).toBeGreaterThanOrEqual(2);
  });

  it("renders an empty-state shell for reports without metro rows", () => {
    render(<ReportV11Detail report={{ ...report, metros: [] }} />);

    expect(screen.getByText("This report does not include metro score data yet.")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: /next steps/i })).not.toBeInTheDocument();
  });
});
