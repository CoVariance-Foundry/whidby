/**
 * Post-run cost analysis for the scoring matrix.
 *
 * Reads e2e-results/scoring-matrix-metrics.jsonl and produces a human-readable
 * cost + reliability summary. Run standalone:
 *
 *   npx tsx apps/app/e2e/helpers/cost-report.ts
 */

import * as fs from "fs";
import * as path from "path";
import type { RunMetric } from "./scoring-combos";

const RESULTS_DIR = path.resolve(__dirname, "..", "..", "e2e-results");
const METRICS_FILE = path.join(RESULTS_DIR, "scoring-matrix-metrics.jsonl");
const COST_REPORT_FILE = path.join(RESULTS_DIR, "cost-report.json");

interface CostEstimate {
  perRunDfsUsd: { low: number; mid: number; high: number };
  perRunLlmUsd: { low: number; mid: number; high: number };
  perRunTotalUsd: { low: number; mid: number; high: number };
}

const COST_ESTIMATE: CostEstimate = {
  perRunDfsUsd:   { low: 0.20, mid: 0.45, high: 0.80 },
  perRunLlmUsd:   { low: 0.01, mid: 0.04, high: 0.08 },
  perRunTotalUsd: { low: 0.21, mid: 0.49, high: 0.88 },
};

interface ComboSummary {
  combo: string;
  tier: 1 | 2;
  runs: number;
  passes: number;
  fails: number;
  errors: number;
  avgLatencyMs: number;
  minLatencyMs: number;
  maxLatencyMs: number;
  reportIds: string[];
  failMessages: string[];
}

interface CostReport {
  generatedAt: string;
  totalRuns: number;
  totalPasses: number;
  totalFails: number;
  totalErrors: number;
  passRate: string;
  flakeRate: string;
  avgLatencyMs: number;
  estimatedCost: {
    low: string;
    mid: string;
    high: string;
  };
  combos: ComboSummary[];
  topFailures: Array<{ combo: string; count: number; messages: string[] }>;
}

export function generateCostReport(): CostReport | null {
  if (!fs.existsSync(METRICS_FILE)) {
    console.error(`No metrics file found at ${METRICS_FILE}`);
    return null;
  }

  const lines = fs
    .readFileSync(METRICS_FILE, "utf-8")
    .trim()
    .split("\n")
    .filter(Boolean);
  const metrics: RunMetric[] = lines.map((l) => JSON.parse(l));

  if (metrics.length === 0) {
    console.error("Metrics file is empty.");
    return null;
  }

  const byCombo = new Map<string, RunMetric[]>();
  for (const m of metrics) {
    const arr = byCombo.get(m.combo) ?? [];
    arr.push(m);
    byCombo.set(m.combo, arr);
  }

  const combos: ComboSummary[] = [];
  for (const [combo, runs] of byCombo.entries()) {
    const passes = runs.filter((r) => r.status === "pass");
    const fails = runs.filter((r) => r.status === "fail");
    const errors = runs.filter((r) => r.status === "error");
    const latencies = runs.map((r) => r.latencyMs);

    combos.push({
      combo,
      tier: runs[0].tier,
      runs: runs.length,
      passes: passes.length,
      fails: fails.length,
      errors: errors.length,
      avgLatencyMs: Math.round(
        latencies.reduce((a, b) => a + b, 0) / latencies.length,
      ),
      minLatencyMs: Math.min(...latencies),
      maxLatencyMs: Math.max(...latencies),
      reportIds: passes.map((r) => r.reportId).filter(Boolean) as string[],
      failMessages: [...new Set(fails.map((r) => r.errorMessage).filter(Boolean) as string[])],
    });
  }
  combos.sort((a, b) => a.tier - b.tier || a.combo.localeCompare(b.combo));

  const totalPasses = metrics.filter((m) => m.status === "pass").length;
  const totalFails = metrics.filter((m) => m.status === "fail").length;
  const totalErrors = metrics.filter((m) => m.status === "error").length;

  // Flake rate: combos that had both passes and fails across repeats
  const flakyCombos = combos.filter((c) => c.passes > 0 && (c.fails > 0 || c.errors > 0));
  const flakeRate =
    combos.length > 0
      ? `${((flakyCombos.length / combos.length) * 100).toFixed(1)}%`
      : "N/A";

  const avgLatencyMs =
    metrics.length > 0
      ? Math.round(metrics.reduce((s, m) => s + m.latencyMs, 0) / metrics.length)
      : 0;

  const successfulRuns = totalPasses;

  const topFailures = combos
    .filter((c) => c.fails + c.errors > 0)
    .sort((a, b) => b.fails + b.errors - (a.fails + a.errors))
    .slice(0, 5)
    .map((c) => ({
      combo: c.combo,
      count: c.fails + c.errors,
      messages: c.failMessages,
    }));

  const report: CostReport = {
    generatedAt: new Date().toISOString(),
    totalRuns: metrics.length,
    totalPasses,
    totalFails,
    totalErrors,
    passRate:
      metrics.length > 0
        ? `${((totalPasses / metrics.length) * 100).toFixed(1)}%`
        : "N/A",
    flakeRate,
    avgLatencyMs,
    estimatedCost: {
      low: `$${(successfulRuns * COST_ESTIMATE.perRunTotalUsd.low).toFixed(2)}`,
      mid: `$${(successfulRuns * COST_ESTIMATE.perRunTotalUsd.mid).toFixed(2)}`,
      high: `$${(successfulRuns * COST_ESTIMATE.perRunTotalUsd.high).toFixed(2)}`,
    },
    combos,
    topFailures,
  };

  fs.mkdirSync(RESULTS_DIR, { recursive: true });
  fs.writeFileSync(COST_REPORT_FILE, JSON.stringify(report, null, 2));
  return report;
}

export function printCostReport(report: CostReport): void {
  console.log("\n╔══════════════════════════════════════════════════╗");
  console.log("║         SCORING MATRIX — COST REPORT             ║");
  console.log("╠══════════════════════════════════════════════════╣");
  console.log(`║  Generated:    ${report.generatedAt}`);
  console.log(`║  Total runs:   ${report.totalRuns}`);
  console.log(`║  Pass/Fail/Err: ${report.totalPasses}/${report.totalFails}/${report.totalErrors}`);
  console.log(`║  Pass rate:    ${report.passRate}`);
  console.log(`║  Flake rate:   ${report.flakeRate}`);
  console.log(`║  Avg latency:  ${report.avgLatencyMs}ms`);
  console.log("╠══════════════════════════════════════════════════╣");
  console.log("║  ESTIMATED COST (successful runs only)           ║");
  console.log(`║  Low:   ${report.estimatedCost.low}`);
  console.log(`║  Mid:   ${report.estimatedCost.mid}`);
  console.log(`║  High:  ${report.estimatedCost.high}`);
  console.log("╠══════════════════════════════════════════════════╣");
  console.log("║  PER-COMBO BREAKDOWN                             ║");

  for (const c of report.combos) {
    const bar = c.passes > 0 ? "✓" : "✗";
    console.log(
      `║  ${bar} [T${c.tier}] ${c.combo.padEnd(22)} ${c.passes}/${c.runs} pass  avg=${c.avgLatencyMs}ms`,
    );
  }

  if (report.topFailures.length > 0) {
    console.log("╠══════════════════════════════════════════════════╣");
    console.log("║  TOP FAILURES                                    ║");
    for (const f of report.topFailures) {
      console.log(`║  ${f.combo}: ${f.count} failures`);
      for (const m of f.messages.slice(0, 2)) {
        console.log(`║    → ${m.slice(0, 60)}`);
      }
    }
  }

  console.log("╚══════════════════════════════════════════════════╝\n");
}

// Run standalone
if (require.main === module) {
  const report = generateCostReport();
  if (report) {
    printCostReport(report);
    console.log(`Full report written to: ${COST_REPORT_FILE}`);
  }
}
