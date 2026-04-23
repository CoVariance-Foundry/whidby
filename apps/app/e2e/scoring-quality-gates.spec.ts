import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import type { RunMetric } from "./helpers/scoring-combos";
import { generateCostReport, printCostReport } from "./helpers/cost-report";

/**
 * Quality gates for the scoring matrix.
 *
 * Run AFTER the scoring-matrix suite completes:
 *   npx playwright test scoring-quality-gates --project=scoring-matrix
 *
 * Reads the JSONL metrics emitted by scoring-matrix.spec.ts and enforces hard
 * thresholds on pass rate, flakiness, and failure diagnostics. Generates the
 * final cost report.
 */

const RESULTS_DIR = path.resolve(__dirname, "..", "e2e-results");
const METRICS_FILE = path.join(RESULTS_DIR, "scoring-matrix-metrics.jsonl");

function loadMetrics(): RunMetric[] {
  if (!fs.existsSync(METRICS_FILE)) return [];
  return fs
    .readFileSync(METRICS_FILE, "utf-8")
    .trim()
    .split("\n")
    .filter(Boolean)
    .map((l) => JSON.parse(l));
}

test.describe("Scoring matrix quality gates", () => {
  let metrics: RunMetric[];

  test.beforeAll(() => {
    metrics = loadMetrics();
    test.skip(
      metrics.length === 0,
      "No scoring matrix metrics found — run scoring-matrix first.",
    );
  });

  test("GATE 1: overall pass rate >= 95%", () => {
    const passes = metrics.filter((m) => m.status === "pass").length;
    const rate = passes / metrics.length;
    test.info().annotations.push({
      type: "pass-rate",
      description: `${(rate * 100).toFixed(1)}% (${passes}/${metrics.length})`,
    });
    expect(
      rate,
      `Pass rate ${(rate * 100).toFixed(1)}% is below the 95% threshold`,
    ).toBeGreaterThanOrEqual(0.95);
  });

  test("GATE 2: no combo fails on ALL repeats (total wipeout)", () => {
    const byCombo = new Map<string, RunMetric[]>();
    for (const m of metrics) {
      const arr = byCombo.get(m.combo) ?? [];
      arr.push(m);
      byCombo.set(m.combo, arr);
    }

    const wipedOut: string[] = [];
    for (const [combo, runs] of byCombo.entries()) {
      if (runs.every((r) => r.status !== "pass")) {
        wipedOut.push(combo);
      }
    }

    expect(
      wipedOut,
      `These combos failed every repeat: ${wipedOut.join(", ")}`,
    ).toHaveLength(0);
  });

  test("GATE 3: Huntsville failure carries diagnostic context (not opaque)", () => {
    const huntsvilleRuns = metrics.filter((m) => m.combo === "huntsville-tree");
    if (huntsvilleRuns.length === 0) {
      test.skip(true, "No Huntsville runs in metrics.");
      return;
    }

    const failures = huntsvilleRuns.filter((m) => m.status === "fail");
    for (const f of failures) {
      expect(
        f.upstreamStatus,
        "Huntsville failure must include upstream_status for triage",
      ).not.toBeNull();
    }
  });

  test("GATE 4: no repeat instability > 40% for any single combo", () => {
    const byCombo = new Map<string, RunMetric[]>();
    for (const m of metrics) {
      const arr = byCombo.get(m.combo) ?? [];
      arr.push(m);
      byCombo.set(m.combo, arr);
    }

    const flaky: Array<{ combo: string; failRate: number }> = [];
    for (const [combo, runs] of byCombo.entries()) {
      if (runs.length < 2) continue;
      const failures = runs.filter((r) => r.status !== "pass").length;
      const failRate = failures / runs.length;
      if (failRate > 0 && failRate < 1 && failRate > 0.4) {
        flaky.push({ combo, failRate });
      }
    }

    expect(
      flaky.map((f) => `${f.combo} (${(f.failRate * 100).toFixed(0)}%)`),
      "Combos with >40% flake rate across repeats",
    ).toHaveLength(0);
  });

  test("GATE 5: average latency under 90 seconds", () => {
    const avgMs =
      metrics.reduce((s, m) => s + m.latencyMs, 0) / metrics.length;
    test.info().annotations.push({
      type: "avg-latency",
      description: `${Math.round(avgMs)}ms`,
    });
    expect(
      avgMs,
      `Average latency ${Math.round(avgMs)}ms exceeds 90s threshold`,
    ).toBeLessThan(90_000);
  });

  test("FINAL: generate cost report", () => {
    const report = generateCostReport();
    expect(report).not.toBeNull();
    if (report) {
      printCostReport(report);
      test.info().annotations.push({
        type: "cost-report",
        description: JSON.stringify(report.estimatedCost),
      });
    }
  });
});
