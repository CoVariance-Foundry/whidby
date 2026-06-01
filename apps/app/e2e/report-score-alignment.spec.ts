import { expect, test } from "@playwright/test";
import { signIn } from "./helpers/auth";

type ReportListRow = {
  id: string;
  niche: string;
  city: string;
  opportunity_score: number | null;
  spec_version: string;
};

type ScoreMap = Record<string, number | undefined>;

type ReportDetailResponse = {
  status?: string;
  report?: {
    spec_version?: string;
    metros?: Array<{
      scores?: ScoreMap;
    }>;
  };
};

const SCORE_LABELS: Array<[string, string]> = [
  ["Demand", "demand"],
  ["Organic ease", "organic_competition"],
  ["Local ease", "local_competition"],
  ["Monetization", "monetization"],
  ["AI resilience", "ai_resilience"],
  ["Opportunity", "opportunity"],
];

test.describe("Report score alignment", () => {
  test("list and detail pages render scores from authenticated report APIs", async ({
    page,
  }) => {
    await signIn(page, { expectLandOn: /\/(reports|$)/ });

    await page.goto("/reports");
    await page.waitForLoadState("networkidle");

    const listBody = await page.evaluate(async () => {
      const response = await fetch("/api/agent/reports?limit=20");
      return response.json();
    }) as { status?: string; reports?: ReportListRow[] };

    expect(listBody.status).toBe("success");
    const report = listBody.reports?.find(
      (row): row is ReportListRow & { opportunity_score: number } =>
        typeof row.opportunity_score === "number" && row.spec_version === "2.0",
    );
    if (!report) throw new Error("expected at least one V2 scored report row");

    const rowLink = page.getByRole("link", {
      name: `Open report for ${report.niche} in ${report.city}`,
    }).first();
    const rowArticle = rowLink.locator("xpath=ancestor::article");
    await expect(rowArticle).toBeVisible();
    await expect(
      rowArticle.getByText(String(report.opportunity_score), { exact: true }),
    ).toBeVisible();

    const detailBody = await page.evaluate(async (reportId) => {
      const response = await fetch(`/api/agent/reports/${reportId}`);
      return response.json();
    }, report.id) as ReportDetailResponse;
    const scores = detailBody.report?.metros?.[0]?.scores;
    expect(detailBody.status).toBe("success");
    expect(scores, "expected report detail scores").toBeTruthy();
    expect(report.opportunity_score).toBe(Math.round(scores?.opportunity as number));
    expect(detailBody.report?.spec_version).toBe(report.spec_version);

    await page.goto(`/reports/${report.id}`);
    await page.waitForLoadState("networkidle");

    const headline = page.getByRole("region", { name: "Headline scores" });
    await expect(headline).toBeVisible();
    await expect(page.getByText(`v${report.spec_version}`, { exact: true })).toBeVisible();
    const headlineText = await headline.textContent();

    for (const [label, key] of SCORE_LABELS) {
      const value = scores?.[key];
      expect(typeof value, `${label} score missing from detail API`).toBe("number");
      expect(headlineText).toContain(label);
      expect(headlineText).toContain(String(Math.round(value as number)));
    }
  });
});
