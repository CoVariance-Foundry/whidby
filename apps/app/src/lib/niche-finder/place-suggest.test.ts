// Mirror of apps/admin/src/lib/niche-finder/place-suggest.test.ts. Keep in sync until lifted to packages/.

import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchMetroSuggestions } from "@/lib/niche-finder/metro-suggest";
import { fetchPlaceSuggestions } from "@/lib/niche-finder/place-suggest";

vi.mock("@/lib/niche-finder/metro-suggest", () => ({
  fetchMetroSuggestions: vi.fn(),
}));

describe("fetchPlaceSuggestions", () => {
  afterEach(() => {
    vi.resetAllMocks();
  });

  it("falls back to metro suggestions when place JSON parsing fails", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response("{not-json", { status: 200 }),
    );
    vi.mocked(fetchMetroSuggestions).mockResolvedValue([
      {
        cbsa_code: "38060",
        city: "Phoenix",
        state: "AZ",
        cbsa_name: "Phoenix-Mesa-Chandler, AZ",
        population: 4946145,
      },
    ]);

    const rows = await fetchPlaceSuggestions("phoenix", 8);

    expect(fetchMetroSuggestions).toHaveBeenCalledWith("phoenix", 8, undefined);
    expect(rows).toEqual([
      {
        city: "Phoenix",
        region: "AZ",
        country: "US",
      },
    ]);
  });
});
