// @vitest-environment jsdom
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
    const sourceContext = screen.getByRole("region", { name: /report source context/i });
    expect(within(sourceContext).getByText("Strategy")).toBeInTheDocument();
    expect(within(sourceContext).getByText("Easy Win")).toBeInTheDocument();
    expect(within(sourceContext).getByText("City")).toBeInTheDocument();
    expect(within(sourceContext).getByText("Phoenix-Mesa-Chandler, AZ")).toBeInTheDocument();
    expect(within(sourceContext).getByText("Service")).toBeInTheDocument();
    expect(within(sourceContext).getByText("plumber")).toBeInTheDocument();
    expect(within(sourceContext).getByText("Segment / report depth")).toBeInTheDocument();
    expect(within(sourceContext).getByText("Standard report")).toBeInTheDocument();
    expect(within(sourceContext).getByText("AI threshold")).toBeInTheDocument();
    expect(within(sourceContext).getByText(/flags scores below this value/i)).toBeInTheDocument();
    expect(within(sourceContext).getByText("Flagged markets visible")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /score and verdict/i })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /signal scores/i })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /score breakdown/i })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /evidence/i })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /next steps/i })).toBeInTheDocument();
    expect(screen.getAllByText("AI Resilience").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Confidence: 90").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Strong local service opportunity.").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /continue to gbp blitz/i })).toHaveAttribute(
      "href",
      expect.stringContaining("/strategies/gbp_blitz?"),
    );
    expect(screen.getByText(/expand & conquer requires a ranked site/i)).toBeInTheDocument();
    expect(screen.getByText(/future portfolio planning node/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /run competitor intel/i })).toHaveAttribute(
      "href",
      expect.stringContaining("report_id=rpt_123"),
    );
  });

  it("explains confidence through the shared glossary tooltip inside the report", async () => {
    const user = userEvent.setup();
    render(<ReportV11Detail report={report} />);

    const button = screen.getByRole("button", { name: /what is source confidence/i });
    expect(button).toHaveAttribute("aria-expanded", "false");

    await user.click(button);

    const tooltip = screen.getByRole("tooltip");
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(button).toHaveAttribute("aria-describedby", tooltip.id);
    expect(tooltip).toHaveTextContent(/how much evidence supports the current market read/i);
    expect(tooltip).toHaveTextContent(/sparse or degraded data can lower confidence/i);
  });

  it("flags AI Resilience scores below the default threshold of 40", () => {
    render(
      <ReportV11Detail
        report={{
          ...report,
          metros: [
            {
              ...report.metros[0],
              scores: {
                ...report.metros[0].scores,
                ai_resilience: 32,
              },
            },
          ],
        }}
      />,
    );

    expect(screen.getAllByText("AI resilience flagged")).toHaveLength(2);
    expect(screen.getAllByLabelText(/AI Resilience flagged: score 32 below threshold 40/i)).toHaveLength(2);
  });

  it("uses report user-state modifier threshold when available", () => {
    render(
      <ReportV11Detail
        report={{
          ...report,
          meta: {
            ai_resilience_modifier: {
              threshold: 30,
              hide_flagged: true,
            },
          },
          metros: [
            {
              ...report.metros[0],
              scores: {
                ...report.metros[0].scores,
                ai_resilience: 32,
              },
            },
          ],
        }}
      />,
    );

    const sourceContext = screen.getByRole("region", { name: /report source context/i });
    expect(within(sourceContext).getByText("Hide flagged on")).toBeInTheDocument();
    expect(screen.getByText("AI threshold: 30")).toBeInTheDocument();
    expect(screen.queryByText("Run metadata")).not.toBeInTheDocument();
    expect(screen.queryByText("AI resilience flagged")).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/below threshold 40/i)).not.toBeInTheDocument();
  });

  it("ignores top-level report meta keys that are not explicit AI modifier state", () => {
    render(
      <ReportV11Detail
        report={{
          ...report,
          meta: {
            threshold: 90,
            hide_flagged: true,
          },
          metros: [
            {
              ...report.metros[0],
              scores: {
                ...report.metros[0].scores,
                ai_resilience: 85,
              },
            },
          ],
        }}
      />,
    );

    expect(screen.getByText("AI threshold: 40")).toBeInTheDocument();
    expect(screen.queryByText("AI threshold: 90")).not.toBeInTheDocument();
    expect(screen.queryByText("AI resilience flagged")).not.toBeInTheDocument();
    expect(screen.queryByText("Run metadata")).not.toBeInTheDocument();
  });

  it("renders an unlocked Expand & Conquer next step when ranked-site context is supplied", () => {
    render(
      <ReportV11Detail
        report={{ ...report, strategy_profile: "replication" }}
        nextStepContext={{ has_ranked_site_declaration: true }}
      />,
    );

    expect(screen.getByRole("link", { name: /continue to expand & conquer/i })).toHaveAttribute(
      "href",
      expect.stringContaining("/strategies/expand_conquer?"),
    );
    expect(screen.queryByText(/requires a ranked site/i)).not.toBeInTheDocument();
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
                demand: undefined as unknown as number,
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
    expect(screen.getAllByText("\u2014").length).toBeGreaterThan(0);
    expect(screen.getByText(/not scored yet/i)).toBeInTheDocument();
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
