import { describe, expect, it, vi } from "vitest";
import { loadExploreData } from "./load-explore-data";

type FakeRow = Record<string, unknown>;

interface FakeResult {
  data: FakeRow[] | null;
  error: { message: string } | null;
}

interface QueryState {
  eqFilters: Array<{ column: string; value: unknown }>;
  inFilters: Array<{ column: string; values: unknown[] }>;
}

const OPTIONAL_REFRESH_TABLES = new Set([
  "explore_latest_target_scores",
  "explore_target_trends",
  "explore_refresh_targets",
]);

function result(data: FakeRow[]): FakeResult {
  return { data, error: null };
}

function makeClient(responses: Record<string, FakeResult[]>) {
  const calls: Array<{ table: string; method: string; args: unknown[] }> = [];

  const from = vi.fn((table: string) => {
    const queryState: QueryState = {
      eqFilters: [],
      inFilters: [],
    };
    const builder = {
      select: vi.fn((...args: unknown[]) => {
        calls.push({ table, method: "select", args });
        return builder;
      }),
      is: vi.fn((...args: unknown[]) => {
        calls.push({ table, method: "is", args });
        return builder;
      }),
      order: vi.fn((...args: unknown[]) => {
        calls.push({ table, method: "order", args });
        return builder;
      }),
      in: vi.fn((...args: unknown[]) => {
        calls.push({ table, method: "in", args });
        const [column, values] = args;
        queryState.inFilters.push({
          column: String(column),
          values: Array.isArray(values) ? values : [],
        });
        return builder;
      }),
      eq: vi.fn((...args: unknown[]) => {
        calls.push({ table, method: "eq", args });
        const [column, value] = args;
        queryState.eqFilters.push({ column: String(column), value });
        return builder;
      }),
      limit: vi.fn((...args: unknown[]) => {
        calls.push({ table, method: "limit", args });
        const next = responses[table]?.shift();
        if (!next) {
          if (OPTIONAL_REFRESH_TABLES.has(table)) {
            return Promise.resolve({
              data: null,
              error: {
                message: `Could not find the table 'public.${table}' in the schema cache`,
              },
            });
          }
          throw new Error(`No fake response for ${table}`);
        }
        if (next.error) {
          return Promise.resolve(next);
        }

        const limit = typeof args[0] === "number" ? args[0] : Number(args[0]);
        const data = (next.data ?? [])
          .filter((row) =>
            queryState.eqFilters.every((filter) => row[filter.column] === filter.value)
          )
          .filter((row) =>
            queryState.inFilters.every((filter) =>
              filter.values.includes(row[filter.column])
            )
          );

        return Promise.resolve({
          data: Number.isFinite(limit) ? data.slice(0, limit) : data,
          error: null,
        });
      }),
    };
    return builder;
  });

  return { client: { from }, calls };
}

describe("loadExploreData", () => {
  it("maps metros and aggregates cached scores by CBSA", async () => {
    const { client } = makeClient({
      metros: [
        result([
          {
            cbsa_code: "38060",
            cbsa_name: "Phoenix-Mesa-Chandler, AZ",
            state: "AZ",
            population: 4_900_000,
            population_class: "metro_1m_5m",
            owner_occupancy_rate: "0.6412",
            median_household_income_usd: 82000,
            median_age_years: "37.4",
            business_density_per_1k: 2.5,
            establishment_growth_yoy: 0.1,
          },
          {
            cbsa_code: "12420",
            cbsa_name: "Austin-Round Rock-Georgetown, TX",
            state: "TX",
            population: 2_300_000,
            population_class: "metro_1m_5m",
            owner_occupancy_rate: 0.58,
            median_household_income_usd: 91000,
            median_age_years: 35.8,
          },
        ]),
      ],
      reports: [
        result([
          {
            id: "report-1",
            created_at: "2026-05-01T12:00:00Z",
            niche_keyword: "roofing",
          },
          {
            id: "report-2",
            created_at: "2026-05-02T12:00:00Z",
            niche_keyword: "plumbing",
          },
        ]),
      ],
      metro_scores: [
        result([
          {
            report_id: "report-2",
            cbsa_code: "38060",
            opportunity_score: 67,
            serp_archetype: null,
            confidence_score: null,
            ai_resilience_score: null,
            ai_exposure: null,
            difficulty_tier: "medium",
          },
          {
            report_id: "report-1",
            cbsa_code: "38060",
            opportunity_score: 81,
            serp_archetype: "PACK_VULN",
            confidence_score: 88,
            ai_resilience_score: 72,
            ai_exposure: "medium",
            difficulty_tier: "low",
          },
        ]),
      ],
    });

    const data = await loadExploreData(client as never);

    expect(data.cities).toHaveLength(2);
    expect(data.cities[0]).toMatchObject({
      cbsa_code: "38060",
      cached_services_count: 2,
      best_opportunity_score: 81,
      average_opportunity_score: 74,
      business_density_per_1k: 2.5,
      establishment_growth_yoy: 0.1,
    });
    expect(data.cities[0].cached_scores.map((score) => score.service)).toEqual([
      "roofing",
      "plumbing",
    ]);
    expect(data.cities[0].cached_scores[0]).toMatchObject({
      report_id: "report-1",
      archetype_id: "PACK_VULN",
      archetype_label: "Pack, vulnerable",
      confidence_score: 88,
      ai_resilience_score: 72,
      ai_exposure: "medium",
      difficulty_tier: "low",
    });
    expect(data.cities[1]).toMatchObject({
      cbsa_code: "12420",
      cached_services_count: 0,
      best_opportunity_score: null,
      average_opportunity_score: null,
      cached_scores: [],
    });
  });

  it("maps latest refresh snapshot freshness onto cached scores", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-05-14T00:00:00Z"));

    try {
      const { client } = makeClient({
        metros: [
          result([
            {
              cbsa_code: "38060",
              cbsa_name: "Phoenix-Mesa-Chandler, AZ",
              state: "AZ",
              population: 4_900_000,
              population_class: "metro_1m_5m",
              owner_occupancy_rate: null,
              median_household_income_usd: null,
              median_age_years: null,
            },
          ]),
        ],
        reports: [
          result([
            {
              id: "report-1",
              created_at: "2026-04-01T12:00:00Z",
              niche_keyword: "roofing",
            },
          ]),
        ],
        metro_scores: [
          result([
            {
              report_id: "report-1",
              cbsa_code: "38060",
              opportunity_score: 81,
              serp_archetype: "LOCAL_PACK_VULNERABLE",
              confidence_score: null,
              ai_resilience_score: null,
              ai_exposure: null,
              difficulty_tier: null,
            },
          ]),
        ],
        explore_latest_target_scores: [
          result([
            {
              target_id: "target-1",
              report_id: "report-1",
              cbsa_code: "38060",
              scored_at: "2026-04-01T12:30:00Z",
              opportunity_score: 81,
            },
          ]),
        ],
        explore_target_trends: [
          result([
            {
              target_id: "target-1",
              report_id: "report-1",
              cbsa_code: "38060",
              scored_at: "2026-04-01T12:30:00Z",
              opportunity_delta: -4,
            },
          ]),
        ],
        explore_refresh_targets: [
          result([
            {
              id: "target-1",
              next_refresh_at: "2026-05-01T12:30:00Z",
            },
          ]),
        ],
      });

      const data = await loadExploreData(client as never);

      expect(data.cities[0].cached_scores[0]).toMatchObject({
        report_id: "report-1",
        refresh_target_id: "target-1",
        last_refreshed_at: "2026-04-01T12:30:00Z",
        next_refresh_at: "2026-05-01T12:30:00Z",
        stale_after_days: 30,
        is_stale: true,
        opportunity_delta: -4,
      });
    } finally {
      vi.useRealTimers();
    }
  });

  it("keeps cached scores when refresh views are missing", async () => {
    const { client } = makeClient({
      metros: [
        result([
          {
            cbsa_code: "38060",
            cbsa_name: "Phoenix-Mesa-Chandler, AZ",
            state: "AZ",
            population: 4_900_000,
            population_class: "metro_1m_5m",
            owner_occupancy_rate: null,
            median_household_income_usd: null,
            median_age_years: null,
          },
        ]),
      ],
      reports: [
        result([
          {
            id: "report-1",
            created_at: "2026-05-01T12:00:00Z",
            niche_keyword: "roofing",
          },
        ]),
      ],
      metro_scores: [
        result([
          {
            report_id: "report-1",
            cbsa_code: "38060",
            opportunity_score: 81,
            serp_archetype: "LOCAL_PACK_VULNERABLE",
            confidence_score: null,
            ai_resilience_score: null,
            ai_exposure: null,
            difficulty_tier: null,
          },
        ]),
      ],
      explore_latest_target_scores: [
        {
          data: null,
          error: {
            message:
              "Could not find the table 'public.explore_latest_target_scores' in the schema cache",
          },
        },
      ],
    });

    const data = await loadExploreData(client as never);
    const score = data.cities[0].cached_scores[0];

    expect(score).toMatchObject({
      report_id: "report-1",
      opportunity_score: 81,
    });
    expect(score).not.toHaveProperty("refresh_target_id");
    expect(score).not.toHaveProperty("last_refreshed_at");
  });

  it("keeps latest freshness when trend view is missing", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-05-14T00:00:00Z"));

    try {
      const { client } = makeClient({
        metros: [
          result([
            {
              cbsa_code: "38060",
              cbsa_name: "Phoenix-Mesa-Chandler, AZ",
              state: "AZ",
              population: 4_900_000,
              population_class: "metro_1m_5m",
              owner_occupancy_rate: null,
              median_household_income_usd: null,
              median_age_years: null,
            },
          ]),
        ],
        reports: [
          result([
            {
              id: "report-1",
              created_at: "2026-05-01T12:00:00Z",
              niche_keyword: "roofing",
            },
          ]),
        ],
        metro_scores: [
          result([
            {
              report_id: "report-1",
              cbsa_code: "38060",
              opportunity_score: 81,
              serp_archetype: "LOCAL_PACK_VULNERABLE",
              confidence_score: null,
              ai_resilience_score: null,
              ai_exposure: null,
              difficulty_tier: null,
            },
          ]),
        ],
        explore_latest_target_scores: [
          result([
            {
              target_id: "target-1",
              report_id: "report-1",
              cbsa_code: "38060",
              scored_at: "2026-05-01T12:30:00Z",
              opportunity_score: 81,
            },
          ]),
        ],
        explore_target_trends: [
          {
            data: null,
            error: {
              message:
                "Could not find the table 'public.explore_target_trends' in the schema cache",
            },
          },
        ],
        explore_refresh_targets: [
          result([
            {
              id: "target-1",
              next_refresh_at: "2026-06-01T12:30:00Z",
            },
          ]),
        ],
      });

      const data = await loadExploreData(client as never);

      expect(data.cities[0].cached_scores[0]).toMatchObject({
        report_id: "report-1",
        refresh_target_id: "target-1",
        last_refreshed_at: "2026-05-01T12:30:00Z",
        next_refresh_at: "2026-06-01T12:30:00Z",
        stale_after_days: 30,
        is_stale: false,
        opportunity_delta: null,
      });
    } finally {
      vi.useRealTimers();
    }
  });

  it("throws refresh view contract errors that do not identify a missing source", async () => {
    const { client } = makeClient({
      metros: [
        result([
          {
            cbsa_code: "38060",
            cbsa_name: "Phoenix-Mesa-Chandler, AZ",
            state: "AZ",
            population: 4_900_000,
            population_class: "metro_1m_5m",
            owner_occupancy_rate: null,
            median_household_income_usd: null,
            median_age_years: null,
          },
        ]),
      ],
      reports: [
        result([
          {
            id: "report-1",
            created_at: "2026-05-01T12:00:00Z",
            niche_keyword: "roofing",
          },
        ]),
      ],
      metro_scores: [
        result([
          {
            report_id: "report-1",
            cbsa_code: "38060",
            opportunity_score: 81,
            serp_archetype: "LOCAL_PACK_VULNERABLE",
            confidence_score: null,
            ai_resilience_score: null,
            ai_exposure: null,
            difficulty_tier: null,
          },
        ]),
      ],
      explore_latest_target_scores: [
        {
          data: null,
          error: { message: "column opportunity_delta does not exist" },
        },
      ],
    });

    await expect(loadExploreData(client as never)).rejects.toThrow(
      "loadExploreData explore_latest_target_scores: column opportunity_delta does not exist"
    );
  });

  it("retries reports without archived_at when the column is missing", async () => {
    const { client, calls } = makeClient({
      metros: [
        result([
          {
            cbsa_code: "38060",
            cbsa_name: "Phoenix-Mesa-Chandler, AZ",
            state: "AZ",
            population: 4_900_000,
            population_class: "metro_1m_5m",
            owner_occupancy_rate: null,
            median_household_income_usd: null,
            median_age_years: null,
          },
        ]),
      ],
      reports: [
        {
          data: null,
          error: { message: 'column reports.archived_at does not exist' },
        },
        result([]),
      ],
    });

    const data = await loadExploreData(client as never);

    expect(data.cities).toHaveLength(1);
    expect(calls.filter((call) => call.table === "reports" && call.method === "limit")).toHaveLength(2);
    expect(calls.some((call) => call.table === "metro_scores")).toBe(false);
  });

  it("retries metros with the base select when optional metric columns are missing", async () => {
    const { client, calls } = makeClient({
      metros: [
        {
          data: null,
          error: {
            message:
              "Could not find the 'business_density_per_1k' column of 'metros' in the schema cache",
          },
        },
        result([
          {
            cbsa_code: "38060",
            cbsa_name: "Phoenix-Mesa-Chandler, AZ",
            state: "AZ",
            population: 4_900_000,
            population_class: "metro_1m_5m",
            owner_occupancy_rate: null,
            median_household_income_usd: null,
            median_age_years: null,
          },
        ]),
      ],
      reports: [result([])],
    });

    const data = await loadExploreData(client as never);

    expect(data.cities[0]).toMatchObject({
      cbsa_code: "38060",
      business_density_per_1k: null,
      establishment_growth_yoy: null,
    });

    const metroSelects = calls.filter(
      (call) => call.table === "metros" && call.method === "select"
    );
    expect(metroSelects).toHaveLength(2);
    expect(String(metroSelects[0].args[0])).toContain("business_density_per_1k");
    expect(String(metroSelects[0].args[0])).toContain("establishment_growth_yoy");
    expect(String(metroSelects[1].args[0])).not.toContain(
      "business_density_per_1k"
    );
    expect(String(metroSelects[1].args[0])).not.toContain(
      "establishment_growth_yoy"
    );
  });

  it("normalizes backend archetype enum values to app archetype ids", async () => {
    const { client } = makeClient({
      metros: [
        result([
          {
            cbsa_code: "38060",
            cbsa_name: "Phoenix-Mesa-Chandler, AZ",
            state: "AZ",
            population: 4_900_000,
            population_class: "metro_1m_5m",
            owner_occupancy_rate: null,
            median_household_income_usd: null,
            median_age_years: null,
          },
        ]),
      ],
      reports: [
        result([
          {
            id: "report-1",
            created_at: "2026-05-01T12:00:00Z",
            niche_keyword: "roofing",
          },
          {
            id: "report-2",
            created_at: "2026-05-02T12:00:00Z",
            niche_keyword: "plumbing",
          },
          {
            id: "report-3",
            created_at: "2026-05-03T12:00:00Z",
            niche_keyword: "hvac",
          },
        ]),
      ],
      metro_scores: [
        result([
          {
            report_id: "report-3",
            cbsa_code: "38060",
            opportunity_score: 20,
            serp_archetype: "FRAGMENTED_COMPETITIVE",
            ai_exposure: null,
            difficulty_tier: null,
          },
          {
            report_id: "report-2",
            cbsa_code: "38060",
            opportunity_score: 20,
            serp_archetype: "AGGREGATOR_DOMINATED",
            ai_exposure: null,
            difficulty_tier: null,
          },
          {
            report_id: "report-1",
            cbsa_code: "38060",
            opportunity_score: 20,
            serp_archetype: "LOCAL_PACK_VULNERABLE",
            ai_exposure: null,
            difficulty_tier: null,
          },
        ]),
      ],
    });

    const data = await loadExploreData(client as never);

    expect(data.cities[0].cached_scores.map((score) => score.archetype_id)).toEqual([
      "FRAG_COMP",
      "AGG",
      "PACK_VULN",
    ]);
    expect(data.cities[0].cached_scores.map((score) => score.archetype_label)).toEqual([
      "Fragmented, comp.",
      "Aggregator‑dominated",
      "Pack, vulnerable",
    ]);
  });

  it("collapses duplicate service scores by keeping the newest report per CBSA", async () => {
    const { client } = makeClient({
      metros: [
        result([
          {
            cbsa_code: "38060",
            cbsa_name: "Phoenix-Mesa-Chandler, AZ",
            state: "AZ",
            population: 4_900_000,
            population_class: "metro_1m_5m",
            owner_occupancy_rate: null,
            median_household_income_usd: null,
            median_age_years: null,
          },
        ]),
      ],
      reports: [
        result([
          {
            id: "older-roofing",
            created_at: "2026-05-01T12:00:00Z",
            niche_keyword: "roofing",
          },
          {
            id: "newer-roofing",
            created_at: "2026-05-03T12:00:00Z",
            niche_keyword: "roofing",
          },
          {
            id: "plumbing",
            created_at: "2026-05-02T12:00:00Z",
            niche_keyword: "plumbing",
          },
        ]),
      ],
      metro_scores: [
        result([
          {
            report_id: "newer-roofing",
            cbsa_code: "38060",
            opportunity_score: 50,
            serp_archetype: "LOCAL_PACK_ESTABLISHED",
            ai_exposure: null,
            difficulty_tier: null,
          },
          {
            report_id: "plumbing",
            cbsa_code: "38060",
            opportunity_score: 70,
            serp_archetype: "FRAGMENTED_WEAK",
            ai_exposure: null,
            difficulty_tier: null,
          },
          {
            report_id: "older-roofing",
            cbsa_code: "38060",
            opportunity_score: 90,
            serp_archetype: "LOCAL_PACK_VULNERABLE",
            ai_exposure: null,
            difficulty_tier: null,
          },
        ]),
      ],
    });

    const data = await loadExploreData(client as never);

    expect(data.cities[0]).toMatchObject({
      cached_services_count: 2,
      best_opportunity_score: 70,
      average_opportunity_score: 60,
    });
    expect(data.cities[0].cached_scores.map((score) => score.report_id)).toEqual([
      "plumbing",
      "newer-roofing",
    ]);
    expect(data.cities[0].cached_scores.map((score) => score.service)).toEqual([
      "plumbing",
      "roofing",
    ]);
  });

  it("skips score lookup when no metros are loaded", async () => {
    const { client, calls } = makeClient({
      metros: [result([])],
      reports: [
        result([
          {
            id: "report-1",
            created_at: "2026-05-01T12:00:00Z",
            niche_keyword: "roofing",
          },
        ]),
      ],
    });

    const data = await loadExploreData(client as never);

    expect(data.cities).toEqual([]);
    expect(calls.some((call) => call.table === "metro_scores")).toBe(false);
  });

  it("batches score lookups by loaded reports and visible CBSAs", async () => {
    const fillerReports = Array.from({ length: 498 }, (_, index) => ({
      id: `filler-${index}`,
      created_at: `2026-05-03T00:${String(index).padStart(2, "0")}:00Z`,
      niche_keyword: `service-${index}`,
    }));
    const outsideScores = fillerReports.flatMap((report, index) => [
      {
        report_id: report.id,
        cbsa_code: `9${String(index).padStart(4, "0")}`,
        opportunity_score: index % 100,
        serp_archetype: "MIXED",
        ai_exposure: null,
        difficulty_tier: null,
      },
      {
        report_id: report.id,
        cbsa_code: `8${String(index).padStart(4, "0")}`,
        opportunity_score: index % 100,
        serp_archetype: "MIXED",
        ai_exposure: null,
        difficulty_tier: null,
      },
    ]);
    const scoreRows = [
      ...outsideScores,
      {
        report_id: "newer-roofing",
        cbsa_code: "38060",
        opportunity_score: 55,
        serp_archetype: "LOCAL_PACK_ESTABLISHED",
        ai_exposure: null,
        difficulty_tier: null,
      },
      {
        report_id: "older-roofing",
        cbsa_code: "38060",
        opportunity_score: 95,
        serp_archetype: "LOCAL_PACK_VULNERABLE",
        ai_exposure: null,
        difficulty_tier: null,
      },
    ];
    const scoreResponses = Array.from({ length: 500 }, () => result(scoreRows));
    const { client, calls } = makeClient({
      metros: [
        result([
          {
            cbsa_code: "38060",
            cbsa_name: "Phoenix-Mesa-Chandler, AZ",
            state: "AZ",
            population: 4_900_000,
            population_class: "metro_1m_5m",
            owner_occupancy_rate: null,
            median_household_income_usd: null,
            median_age_years: null,
          },
        ]),
      ],
      reports: [
        result([
          ...fillerReports,
          {
            id: "newer-roofing",
            created_at: "2026-05-02T12:00:00Z",
            niche_keyword: "roofing",
          },
          {
            id: "older-roofing",
            created_at: "2026-05-01T12:00:00Z",
            niche_keyword: "roofing",
          },
        ]),
      ],
      metro_scores: scoreResponses,
    });

    const data = await loadExploreData(client as never);

    expect(data.cities[0]).toMatchObject({
      cached_services_count: 1,
      best_opportunity_score: 55,
      average_opportunity_score: 55,
    });
    expect(data.cities[0].cached_scores.map((score) => score.report_id)).toEqual([
      "newer-roofing",
    ]);

    const scoreEqCalls = calls.filter(
      (call) => call.table === "metro_scores" && call.method === "eq"
    );
    const reportInCalls = calls.filter(
      (call) =>
        call.table === "metro_scores" &&
        call.method === "in" &&
        call.args[0] === "report_id"
    );
    const cbsaInCalls = calls.filter(
      (call) =>
        call.table === "metro_scores" &&
        call.method === "in" &&
        call.args[0] === "cbsa_code"
    );

    expect(scoreEqCalls).toHaveLength(0);
    expect(reportInCalls.length).toBeGreaterThan(0);
    expect(
      reportInCalls.every(
        (call) => Array.isArray(call.args[1]) && call.args[1].length > 1
      )
    ).toBe(true);
    expect(cbsaInCalls.map((call) => call.args)).toEqual(
      reportInCalls.map(() => ["cbsa_code", ["38060"]])
    );
  });

  it("batches freshness lookups by report and target identifiers", async () => {
    const reports = Array.from({ length: 250 }, (_, index) => ({
      id: `report-${index}`,
      created_at: `2026-05-${String((index % 28) + 1).padStart(2, "0")}T12:00:00Z`,
      niche_keyword: `service-${index}`,
    }));
    const scoreRows = reports.map((report, index) => ({
      report_id: report.id,
      cbsa_code: "38060",
      opportunity_score: index % 100,
      serp_archetype: "MIXED",
      ai_exposure: null,
      difficulty_tier: null,
    }));
    const latestRows = reports.map((report, index) => ({
      target_id: `target-${index}`,
      report_id: report.id,
      cbsa_code: "38060",
      scored_at: report.created_at,
      opportunity_score: index % 100,
    }));
    const trendRows = latestRows.map((row) => ({
      ...row,
      opportunity_delta: 1,
    }));
    const targetRows = latestRows.map((row) => ({
      id: row.target_id,
      next_refresh_at: "2026-06-01T12:00:00Z",
    }));
    const { client, calls } = makeClient({
      metros: [
        result([
          {
            cbsa_code: "38060",
            cbsa_name: "Phoenix-Mesa-Chandler, AZ",
            state: "AZ",
            population: 4_900_000,
            population_class: "metro_1m_5m",
            owner_occupancy_rate: null,
            median_household_income_usd: null,
            median_age_years: null,
          },
        ]),
      ],
      reports: [result(reports)],
      metro_scores: Array.from({ length: 3 }, () => result(scoreRows)),
      explore_latest_target_scores: Array.from({ length: 3 }, () =>
        result(latestRows)
      ),
      explore_target_trends: Array.from({ length: 9 }, () => result(trendRows)),
      explore_refresh_targets: Array.from({ length: 3 }, () => result(targetRows)),
    });

    const data = await loadExploreData(client as never);

    expect(data.cities[0].cached_services_count).toBe(250);

    const latestReportInCalls = calls.filter(
      (call) =>
        call.table === "explore_latest_target_scores" &&
        call.method === "in" &&
        call.args[0] === "report_id"
    );
    const trendReportInCalls = calls.filter(
      (call) =>
        call.table === "explore_target_trends" &&
        call.method === "in" &&
        call.args[0] === "report_id"
    );
    const trendTargetInCalls = calls.filter(
      (call) =>
        call.table === "explore_target_trends" &&
        call.method === "in" &&
        call.args[0] === "target_id"
    );
    const refreshTargetInCalls = calls.filter(
      (call) =>
        call.table === "explore_refresh_targets" &&
        call.method === "in" &&
        call.args[0] === "id"
    );
    const batchedInCalls = [
      ...latestReportInCalls,
      ...trendReportInCalls,
      ...trendTargetInCalls,
      ...refreshTargetInCalls,
    ];

    expect(latestReportInCalls.map((call) => call.args[1])).toEqual([
      reports.slice(0, 100).map((report) => report.id),
      reports.slice(100, 200).map((report) => report.id),
      reports.slice(200).map((report) => report.id),
    ]);
    expect(trendReportInCalls).toHaveLength(9);
    expect(trendTargetInCalls).toHaveLength(9);
    expect(refreshTargetInCalls.map((call) => call.args[1])).toEqual([
      latestRows.slice(0, 100).map((row) => row.target_id),
      latestRows.slice(100, 200).map((row) => row.target_id),
      latestRows.slice(200).map((row) => row.target_id),
    ]);
    expect(
      batchedInCalls.every(
        (call) => Array.isArray(call.args[1]) && call.args[1].length <= 100
      )
    ).toBe(true);
  });
});
