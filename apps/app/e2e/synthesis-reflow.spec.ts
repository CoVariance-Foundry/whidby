import { expect, test, type Page, type Route } from "@playwright/test";
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
      cbsa_code?: string;
      cbsa_name?: string;
      state?: string;
      scores?: ScoreMap;
    }>;
  };
};

async function settlePage(page: Page): Promise<void> {
  await expect(page.locator("body")).toBeVisible();
  await page.waitForLoadState("domcontentloaded");
  await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => {
    // Authenticated app pages may keep analytics or background requests open.
  });
}

async function captureFullPageEvidence(
  page: Page,
  path: string,
): Promise<void> {
  await page
    .addStyleTag({
      content: `
        nextjs-portal,
        [data-nextjs-toast],
        [data-nextjs-dialog-overlay],
        [data-nextjs-dev-tools],
        [data-nextjs-dev-tools-button] {
          display: none !important;
          visibility: hidden !important;
          opacity: 0 !important;
          pointer-events: none !important;
        }
      `,
    })
    .catch(() => {
      // The overlay is dev-only; screenshots remain valid if the selector is absent.
    });
  await page.evaluate(() => {
    document
      .querySelectorAll(
        "nextjs-portal, [data-nextjs-toast], [data-nextjs-dev-tools], [data-nextjs-dev-tools-button]",
      )
      .forEach((element) => element.remove());
  });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path, fullPage: true });
}

async function blockPaidApis(page: Page): Promise<string[]> {
  const paidApiCalls: string[] = [];
  const paidRoutes = [
    "**/api/agent/scoring",
    "**/api/strategies/runs",
    "**/api/competitor-intel/runs",
  ];

  for (const routePattern of paidRoutes) {
    await page.route(routePattern, (route: Route) => {
      paidApiCalls.push(route.request().url());
      return route.fulfill({
        status: 418,
        contentType: "application/json",
        body: JSON.stringify({
          status: "blocked",
          message: "blocked by synthesis reflow E2E",
        }),
      });
    });
  }

  return paidApiCalls;
}

async function loadReportFixture(page: Page) {
  const listBody = (await page.evaluate(async () => {
    const response = await fetch("/api/agent/reports?limit=20");
    return response.json();
  })) as { status?: string; reports?: ReportListRow[] };

  expect(listBody.status).toBe("success");
  const report = listBody.reports?.find(
    (row): row is ReportListRow & { opportunity_score: number } =>
      typeof row.opportunity_score === "number" && row.spec_version === "2.0",
  );
  if (!report) throw new Error("expected at least one V2 scored report row");

  const detailBody = (await page.evaluate(async (reportId) => {
    const response = await fetch(`/api/agent/reports/${reportId}`);
    return response.json();
  }, report.id)) as ReportDetailResponse;

  expect(detailBody.status).toBe("success");
  const metro = detailBody.report?.metros?.[0];
  if (!metro?.scores) throw new Error("expected first report metro with scores");

  return { report, metro };
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

test.describe.serial("synthesis reflow E2E", () => {
  test("runs dashboard to strategy inline result to report detail without paid API calls", async ({
    page,
  }, testInfo) => {
    const paidApiCalls = await blockPaidApis(page);
    await signIn(page, { expectLandOn: /\/(reports|$)/ });

    await page.goto("/");
    await settlePage(page);
    await expect(page.getByRole("heading", { name: /^dashboard$/i })).toBeVisible();
    await expect(
      page
        .locator('[aria-label="Authenticated product navigation"]')
        .getByRole("link", { name: /^strategies$/i }),
    ).toBeVisible();
    await captureFullPageEvidence(page, testInfo.outputPath("synthesis-dashboard.png"));

    const { report, metro } = await loadReportFixture(page);
    const discoveryPayloads: unknown[] = [];
    await page.route("**/api/strategies/discover", async (route) => {
      discoveryPayloads.push(await route.request().postDataJSON());
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          markets: [
            {
              rank: 1,
              opportunity_score: report.opportunity_score,
              city: {
                cbsa_code: metro.cbsa_code,
                name: report.city,
                state: metro.state,
              },
              service: {
                name: report.niche,
              },
              strategy_evidence: [
                "Seeded cached report reused for synthesis path verification.",
              ],
              warnings: [],
              report_id: report.id,
              scores: metro.scores,
              ai_resilience_score: metro.scores.ai_resilience,
            },
          ],
        }),
      });
    });

    await page.goto("/strategies");
    await settlePage(page);
    await expect(page.getByRole("heading", { name: /^strategy path$/i })).toBeVisible();
    await expect(page.getByLabel("B2 strategy path rail")).toBeVisible();

    const easyWinCard = page
      .getByRole("heading", { name: "Easy Win" })
      .locator("xpath=ancestor::article");
    const easyWinButton = easyWinCard.getByRole("button").last();
    if ((await easyWinButton.textContent())?.match(/work this step/i)) {
      await easyWinButton.click();
    }

    await page.getByLabel("City").fill(report.city);
    await page.getByLabel("Service").fill(report.niche);
    await page.getByRole("button", { name: /run discovery/i }).click();

    await expect(
      page.getByText(
        new RegExp(`${escapeRegExp(report.niche)} in ${escapeRegExp(report.city)}`, "i"),
      ),
    ).toBeVisible();
    await expect(page.getByRole("link", { name: /open full report/i })).toHaveAttribute(
      "href",
      `/reports/${report.id}`,
    );
    expect(discoveryPayloads).toHaveLength(1);
    await captureFullPageEvidence(
      page,
      testInfo.outputPath("synthesis-strategy-inline-result.png"),
    );

    await page.getByRole("link", { name: /open full report/i }).click();
    await expect(page).toHaveURL(new RegExp(`/reports/${report.id}$`));
    await settlePage(page);
    await expect(page.getByRole("region", { name: "Report source context" })).toBeVisible();
    await expect(page.getByRole("region", { name: "Score and verdict" })).toBeVisible();
    await expect(page.getByRole("region", { name: "Signal scores" })).toBeVisible();
    await expect(page.getByRole("region", { name: "Next steps" })).toBeVisible();
    expect(paidApiCalls).toEqual([]);
    await captureFullPageEvidence(page, testInfo.outputPath("synthesis-report-detail.png"));
  });
});
