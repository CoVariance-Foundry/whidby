import { describe, expect, it } from "vitest";
import type { FullReportData, ReportMetro } from "@/lib/niche-finder/types";
import {
  buildReportCompetitorIntelHref,
  buildReportExploreHref,
  buildReportNextSteps,
} from "./report-next-steps";

const metro: ReportMetro = {
  cbsa_code: "38060",
  cbsa_name: "Phoenix-Mesa-Chandler, AZ",
  population: 4968450,
  scores: {
    demand: 72,
    organic_competition: 65,
    local_competition: 58,
    monetization: 80,
    ai_resilience: 85,
    opportunity: 74,
  },
};

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
  metros: [metro],
  meta: null,
};

describe("report next steps", () => {
  it("routes Easy Win reports toward GBP Blitz with report, city, service, and CBSA context", () => {
    const steps = buildReportNextSteps({ report, metro });
    const gbpBlitz = steps.find((step) => step.id === "gbp_blitz");
    const expandConquer = steps.find((step) => step.id === "expand_conquer");

    expect(gbpBlitz).toMatchObject({
      kind: "strategy",
      title: "Continue to GBP Blitz",
      state: "available",
      primary: true,
    });
    expect(gbpBlitz?.href).toContain("/strategies/gbp_blitz?");
    expect(gbpBlitz?.href).toContain("from_report=1");
    expect(gbpBlitz?.href).toContain("report_id=rpt_123");
    expect(gbpBlitz?.href).toContain("city=Phoenix-Mesa-Chandler%2C+AZ");
    expect(gbpBlitz?.href).toContain("service=plumber");
    expect(gbpBlitz?.href).toContain("cbsa_code=38060");
    expect(gbpBlitz?.href).toContain("state=AZ");
    expect(expandConquer).toMatchObject({
      state: "locked",
      requirement_label: "Ranked site declared",
    });
    expect(expandConquer?.href).toBeUndefined();
  });

  it("keeps lookalike replication flows locked until ranked-site declaration is present", () => {
    const steps = buildReportNextSteps({
      report: { ...report, strategy_profile: "lookalike_replication" },
      metro,
    });
    const expandConquer = steps.find((step) => step.id === "expand_conquer");

    expect(expandConquer).toMatchObject({
      title: "Expand & Conquer requires a ranked site",
      state: "locked",
      primary: true,
      requirement_label: "Ranked site declared",
    });
    expect(expandConquer?.href).toBeUndefined();
  });

  it("routes lookalike replication flows into Expand & Conquer when ranked-site state is unlocked", () => {
    const steps = buildReportNextSteps({
      report: { ...report, strategy_profile: "replication" },
      metro,
      context: { has_ranked_site_declaration: true },
    });
    const expandConquer = steps.find((step) => step.id === "expand_conquer");
    const portfolioBuilder = steps.find((step) => step.id === "portfolio_builder");

    expect(expandConquer).toMatchObject({
      title: "Continue to Expand & Conquer",
      state: "available",
      primary: true,
    });
    expect(expandConquer?.href).toContain("/strategies/expand_conquer?");
    expect(expandConquer?.href).toContain("reference_city_id=38060");
    expect(expandConquer?.href).toContain("report_id=rpt_123");
    expect(portfolioBuilder).toMatchObject({
      state: "future",
      requirement_label: "Locked",
    });
    expect(portfolioBuilder?.href).toBeUndefined();
  });

  it("keeps Explore and Competitor Intel browsing links contextual", () => {
    expect(buildReportExploreHref(report, metro)).toBe(
      "/explore?service=plumber&state=AZ&from_report=1&report_id=rpt_123",
    );
    expect(buildReportCompetitorIntelHref(report, metro)).toBe(
      "/competitor-intel?report_id=rpt_123&city=Phoenix-Mesa-Chandler%2C+AZ&service=plumber&cbsa_code=38060",
    );
  });
});
