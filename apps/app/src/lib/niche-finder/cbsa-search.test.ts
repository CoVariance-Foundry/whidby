import { describe, expect, it } from "vitest";
import { searchMetros } from "./cbsa-search";

describe("searchMetros", () => {
  it("returns top metros by population for empty or 1-character queries", () => {
    const emptyQueryResults = searchMetros("", 10);
    const oneCharacterResults = searchMetros("a", 10);

    expect(emptyQueryResults).toHaveLength(10);
    expect(oneCharacterResults).toHaveLength(10);
    expect(emptyQueryResults).toEqual(oneCharacterResults);
    expect(emptyQueryResults[0].population).toBeGreaterThanOrEqual(emptyQueryResults[9].population);
  });
});
