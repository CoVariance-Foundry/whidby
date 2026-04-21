import { describe, it, expect } from "vitest";
import { mapReportRow } from "./reports-mapper";

describe("mapReportRow", () => {
  it("extracts opportunity from first metro", () => {
    const row = {
      id: "r1",
      niche_keyword: "roofing",
      geo_target: "Phoenix, AZ",
      created_at: "2026-04-20T00:00:00Z",
      spec_version: "1.1",
      metros: [{ scores: { opportunity: 72 } }],
    };
    expect(mapReportRow(row).opportunity_score).toBe(72);
  });

  it("returns null when metros is missing or empty", () => {
    const row = {
      id: "r1",
      niche_keyword: "roofing",
      geo_target: "Phoenix, AZ",
      created_at: "2026-04-20T00:00:00Z",
      spec_version: "1.1",
      metros: [],
    };
    expect(mapReportRow(row).opportunity_score).toBeNull();
  });

  it("rounds float opportunity to int", () => {
    const row = {
      id: "r1",
      niche_keyword: "roofing",
      geo_target: "Phoenix, AZ",
      created_at: "2026-04-20T00:00:00Z",
      spec_version: "1.1",
      metros: [{ scores: { opportunity: 72.6 } }],
    };
    expect(mapReportRow(row).opportunity_score).toBe(73);
  });

  it("gracefully handles missing scores", () => {
    const row = {
      id: "r1",
      niche_keyword: "roofing",
      geo_target: "Phoenix, AZ",
      created_at: "2026-04-20T00:00:00Z",
      spec_version: "1.1",
      metros: [{ scores: {} }],
    };
    expect(mapReportRow(row).opportunity_score).toBeNull();
  });
});
