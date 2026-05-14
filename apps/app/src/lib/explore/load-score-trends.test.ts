import { describe, expect, it, vi } from "vitest";
import { loadScoreTrends } from "./load-score-trends";

type FakeRow = Record<string, unknown>;

interface FakeResult {
  data: FakeRow[] | null;
  error: { message: string } | null;
}

interface QueryState {
  eqFilters: Array<{ column: string; value: unknown }>;
}

function makeClient(result: FakeResult) {
  const calls: Array<{ method: string; args: unknown[] }> = [];

  const from = vi.fn(() => {
    const queryState: QueryState = {
      eqFilters: [],
    };

    const builder = {
      select: vi.fn((...args: unknown[]) => {
        calls.push({ method: "select", args });
        return builder;
      }),
      eq: vi.fn((...args: unknown[]) => {
        calls.push({ method: "eq", args });
        const [column, value] = args;
        queryState.eqFilters.push({ column: String(column), value });
        return builder;
      }),
      order: vi.fn((...args: unknown[]) => {
        calls.push({ method: "order", args });
        return builder;
      }),
      limit: vi.fn((...args: unknown[]) => {
        calls.push({ method: "limit", args });
        const data = (result.data ?? []).filter((row) =>
          queryState.eqFilters.every((filter) => row[filter.column] === filter.value)
        );

        return Promise.resolve({
          data: result.error ? null : data,
          error: result.error,
        });
      }),
    };

    return builder;
  });

  return { client: { from }, calls };
}

describe("loadScoreTrends", () => {
  it("maps trend rows from explore_target_trends for a refresh target", async () => {
    const { client } = makeClient({
      data: [
        {
          target_id: "target-1",
          scored_at: "2026-05-01T00:00:00Z",
          opportunity_score: 72,
          opportunity_delta: null,
        },
        {
          target_id: "target-2",
          scored_at: "2026-05-02T00:00:00Z",
          opportunity_score: 91,
          opportunity_delta: 8,
        },
        {
          target_id: "target-1",
          scored_at: "2026-05-03T00:00:00Z",
          opportunity_score: "76.5",
          opportunity_delta: "-2.25",
        },
      ],
      error: null,
    });

    await expect(loadScoreTrends(client as never, "target-1")).resolves.toEqual([
      {
        scored_at: "2026-05-01T00:00:00Z",
        opportunity_score: 72,
        opportunity_delta: null,
      },
      {
        scored_at: "2026-05-03T00:00:00Z",
        opportunity_score: 76.5,
        opportunity_delta: -2.25,
      },
    ]);

    expect(client.from).toHaveBeenCalledWith("explore_target_trends");
  });

  it("throws with source context when Supabase returns an error", async () => {
    const { client } = makeClient({
      data: null,
      error: { message: "column opportunity_score does not exist" },
    });

    await expect(loadScoreTrends(client as never, "target-1")).rejects.toThrow(
      "loadScoreTrends explore_target_trends: column opportunity_score does not exist"
    );
  });

  it("returns an empty array when Supabase data is empty or null", async () => {
    const emptyClient = makeClient({ data: [], error: null }).client;
    const nullClient = makeClient({ data: null, error: null }).client;

    await expect(loadScoreTrends(emptyClient as never, "target-1")).resolves.toEqual(
      []
    );
    await expect(loadScoreTrends(nullClient as never, "target-1")).resolves.toEqual(
      []
    );
  });

  it("omits rows with null or invalid scored_at values", async () => {
    const { client } = makeClient({
      data: [
        {
          target_id: "target-1",
          scored_at: null,
          opportunity_score: 72,
          opportunity_delta: 1,
        },
        {
          target_id: "target-1",
          scored_at: "not-a-date",
          opportunity_score: 73,
          opportunity_delta: 2,
        },
        {
          target_id: "target-1",
          scored_at: "2026-05-01T00:00:00Z",
          opportunity_score: 74,
          opportunity_delta: 3,
        },
      ],
      error: null,
    });

    await expect(loadScoreTrends(client as never, "target-1")).resolves.toEqual([
      {
        scored_at: "2026-05-01T00:00:00Z",
        opportunity_score: 74,
        opportunity_delta: 3,
      },
    ]);
  });

  it("applies select, filter, order, and limit with expected args", async () => {
    const { client, calls } = makeClient({
      data: [
        {
          target_id: "target-1",
          scored_at: "2026-05-01T00:00:00Z",
          opportunity_score: 72,
          opportunity_delta: 1,
        },
      ],
      error: null,
    });

    await loadScoreTrends(client as never, "target-1");

    expect(calls).toEqual([
      {
        method: "select",
        args: ["scored_at, opportunity_score, opportunity_delta"],
      },
      { method: "eq", args: ["target_id", "target-1"] },
      { method: "order", args: ["scored_at", { ascending: true }] },
      { method: "limit", args: [24] },
    ]);
  });
});
