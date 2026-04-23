import { test, expect, type Page } from "@playwright/test";
import { signIn } from "./helpers/auth";
import {
  ALL_COMBOS,
  comboToRequestBody,
  type RunMetric,
  type ScoringCombo,
} from "./helpers/scoring-combos";
import * as fs from "fs";
import * as path from "path";

/**
 * 50-Run Scoring Matrix
 *
 * 10 city/service combinations (5 standard + 5 varied) x 5 repeats each.
 *
 * Run with:
 *   npx playwright test scoring-matrix --repeat-each=5 --project=scoring-matrix
 *
 * Or for a quick 10-run calibration (1 repeat each):
 *   npx playwright test scoring-matrix --project=scoring-matrix
 *
 * Results are written to e2e-results/scoring-matrix-metrics.jsonl (one JSON
 * line per run) for post-run analysis.
 */

const SCORING_ENDPOINT = "/api/agent/scoring";
const RESULTS_DIR = path.resolve(__dirname, "..", "e2e-results");
const METRICS_FILE = path.join(RESULTS_DIR, "scoring-matrix-metrics.jsonl");

function appendMetric(metric: RunMetric) {
  fs.mkdirSync(RESULTS_DIR, { recursive: true });
  fs.appendFileSync(METRICS_FILE, JSON.stringify(metric) + "\n");
}

async function authPost(
  page: Page,
  url: string,
  data: Record<string, unknown>,
): Promise<{ status: number; body: Record<string, unknown> }> {
  return page.evaluate(
    async ({ url, data }) => {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      let body: Record<string, unknown>;
      try {
        body = await res.json();
      } catch {
        body = { _parseError: true, _raw: (await res.clone().text()).slice(0, 500) };
      }
      return { status: res.status, body };
    },
    { url, data },
  );
}

// Sign in once per test (each test needs browser context for auth cookies).
test.beforeEach(async ({ page }) => {
  await signIn(page, { expectLandOn: /\/(reports|$)/ });
});

// ── Tier 1: Standard combos (baseline reliability) ───────────────────────────

test.describe("Tier 1 — Standard combos", () => {
  for (const combo of ALL_COMBOS.filter((c) => c.tier === 1)) {
    createScoringTest(combo);
  }
});

// ── Tier 2: Varied combos (edge diversity + bug hunting) ─────────────────────

test.describe("Tier 2 — Varied combos", () => {
  for (const combo of ALL_COMBOS.filter((c) => c.tier === 2)) {
    createScoringTest(combo);
  }
});

function createScoringTest(combo: ScoringCombo) {
  test(
    `${combo.tag} — ${combo.city} + ${combo.service}`,
    async ({ page }, testInfo) => {
      const repeatIndex = testInfo.repeatEachIndex ?? 0;
      const start = Date.now();

      const { status, body } = await authPost(
        page,
        SCORING_ENDPOINT,
        comboToRequestBody(combo),
      );
      const latencyMs = Date.now() - start;

      const metric: RunMetric = {
        combo: combo.tag,
        tier: combo.tier,
        runIndex: repeatIndex,
        status: "error",
        httpStatus: status,
        reportId: null,
        opportunityScore: null,
        latencyMs,
        upstreamStatus: (body?.upstream_status as number) ?? null,
        errorMessage: (body?.message as string) ?? null,
        timestamp: new Date().toISOString(),
      };

      if (status >= 200 && status < 300 && body?.status === "success") {
        metric.status = "pass";
        metric.reportId = (body.report_id as string) ?? null;
        metric.opportunityScore =
          (body.score_result as Record<string, number>)?.opportunity_score ?? null;

        const scoreResult = body.score_result as Record<string, unknown>;
        expect(scoreResult.opportunity_score).toBeGreaterThanOrEqual(0);
        expect(scoreResult.opportunity_score).toBeLessThanOrEqual(100);
        expect(["High", "Medium", "Low"]).toContain(scoreResult.classification_label);
        expect(body.report_id).toBeTruthy();
      } else {
        metric.status = "fail";

        if (status === 502 && body?.upstream_status) {
          test.info().annotations.push({
            type: "structured-failure",
            description: `upstream_status=${body.upstream_status}`,
          });
        }

        expect(body.message ?? body._parseError).toBeDefined();
      }

      appendMetric(metric);
      test.info().annotations.push({
        type: "metric",
        description: JSON.stringify(metric),
      });
    },
  );
}

// ── Post-run summary (runs after all tests in this file) ─────────────────────

test.afterAll(async () => {
  if (!fs.existsSync(METRICS_FILE)) return;

  const lines = fs
    .readFileSync(METRICS_FILE, "utf-8")
    .trim()
    .split("\n")
    .filter(Boolean);
  const metrics: RunMetric[] = lines.map((l) => JSON.parse(l));

  const passes = metrics.filter((m) => m.status === "pass");
  const fails = metrics.filter((m) => m.status === "fail");
  const errors = metrics.filter((m) => m.status === "error");
  const avgLatency =
    metrics.length > 0
      ? Math.round(metrics.reduce((s, m) => s + m.latencyMs, 0) / metrics.length)
      : 0;

  const summary = {
    totalRuns: metrics.length,
    passes: passes.length,
    fails: fails.length,
    errors: errors.length,
    passRate:
      metrics.length > 0
        ? `${((passes.length / metrics.length) * 100).toFixed(1)}%`
        : "N/A",
    avgLatencyMs: avgLatency,
    failedCombos: [...new Set(fails.map((m) => m.combo))],
    errorCombos: [...new Set(errors.map((m) => m.combo))],
    uniqueReportIds: [...new Set(passes.map((m) => m.reportId).filter(Boolean))]
      .length,
  };

  const summaryPath = path.join(RESULTS_DIR, "scoring-matrix-summary.json");
  fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2));

  console.log("\n══════════════════════════════════════════════");
  console.log("  SCORING MATRIX SUMMARY");
  console.log("══════════════════════════════════════════════");
  console.log(`  Total runs:    ${summary.totalRuns}`);
  console.log(`  Passes:        ${summary.passes}`);
  console.log(`  Fails:         ${summary.fails}`);
  console.log(`  Errors:        ${summary.errors}`);
  console.log(`  Pass rate:     ${summary.passRate}`);
  console.log(`  Avg latency:   ${summary.avgLatencyMs}ms`);
  if (summary.failedCombos.length > 0) {
    console.log(`  Failed combos: ${summary.failedCombos.join(", ")}`);
  }
  console.log("══════════════════════════════════════════════\n");
});
