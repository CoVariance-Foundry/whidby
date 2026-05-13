import { describe, expect, it, vi } from "vitest";
import { GET } from "./route";
import { NextRequest } from "next/server";
import { searchMetros } from "@/lib/niche-finder/cbsa-search";

vi.mock("@/lib/niche-finder/cbsa-search", () => ({
  searchMetros: vi.fn(),
}));

describe("GET /api/agent/metros/suggest", () => {
  it("forwards q + limit and returns the upstream list verbatim", async () => {
    const sample = [
      { cbsa_code: "38060", city: "Phoenix", state: "AZ", cbsa_name: "Phoenix-Mesa-Chandler, AZ", population: 4946145 },
    ];
    vi.mocked(searchMetros).mockReturnValue(sample);

    const req = new NextRequest("http://localhost/api/agent/metros/suggest?q=phoe&limit=5");
    const res = await GET(req);

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual(sample);
    expect(searchMetros).toHaveBeenCalledWith("phoe", 5);
  });

  it("returns local results even when query is empty", async () => {
    vi.mocked(searchMetros).mockReturnValue([]);

    const req = new NextRequest("http://localhost/api/agent/metros/suggest?q=");
    const res = await GET(req);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual([]);
    expect(searchMetros).toHaveBeenCalledWith("", 10);
  });
});
