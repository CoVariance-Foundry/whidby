import { describe, it, expect, vi } from "vitest";
import { loadDashboard } from "./load-dashboard";

function makeClient(rows: Array<Record<string, unknown>>) {
  const limit = vi.fn().mockResolvedValue({ data: rows, error: null });
  const order = vi.fn().mockReturnValue({ limit });
  const select = vi.fn().mockReturnValue({ order });
  const from = vi.fn().mockReturnValue({ select });
  return { from } as never;
}

describe("loadDashboard", () => {
  it("returns stats + recent + recommended from reports table", async () => {
    const rows = [
      {
        id: "r1",
        niche_keyword: "roofing",
        geo_target: "Phoenix, AZ",
        created_at: "2026-04-20T12:00:00Z",
        spec_version: "1.1",
        metros: [{ scores: { opportunity: 78 } }],
      },
      {
        id: "r2",
        niche_keyword: "plumbing",
        geo_target: "Austin, TX",
        created_at: "2026-04-19T09:00:00Z",
        spec_version: "1.1",
        metros: [{ scores: { opportunity: 71 } }],
      },
    ];
    const dashboard = await loadDashboard(makeClient(rows));
    expect(dashboard.stats.total_reports).toBe(2);
    expect(dashboard.stats.avg_score).toBe(75); // (78+71)/2 rounded
    expect(dashboard.recent.length).toBe(2);
    expect(dashboard.recent[0].niche).toBe("roofing");
    expect(dashboard.recommended.length).toBe(2);
  });

  it("handles empty reports gracefully", async () => {
    const dashboard = await loadDashboard(makeClient([]));
    expect(dashboard.stats.total_reports).toBe(0);
    expect(dashboard.stats.avg_score).toBe(0);
    expect(dashboard.recent).toEqual([]);
    expect(dashboard.recommended).toEqual([]);
  });
});
