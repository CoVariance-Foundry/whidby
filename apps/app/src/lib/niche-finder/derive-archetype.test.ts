import { describe, it, expect } from "vitest";
import { deriveArchetype } from "./derive-archetype";

describe("deriveArchetype", () => {
  it("returns MIXED when no score is present", () => {
    expect(deriveArchetype({ opportunity_score: null })).toBe("MIXED");
  });
  it("maps high (>=75) to PACK_VULN", () => {
    expect(deriveArchetype({ opportunity_score: 80 })).toBe("PACK_VULN");
  });
  it("maps mid-high (60-74) to FRAG_WEAK", () => {
    expect(deriveArchetype({ opportunity_score: 68 })).toBe("FRAG_WEAK");
  });
  it("maps mid (45-59) to PACK_EST", () => {
    expect(deriveArchetype({ opportunity_score: 50 })).toBe("PACK_EST");
  });
  it("maps low-mid (30-44) to FRAG_COMP", () => {
    expect(deriveArchetype({ opportunity_score: 36 })).toBe("FRAG_COMP");
  });
  it("maps low (<30) to BARREN", () => {
    expect(deriveArchetype({ opportunity_score: 12 })).toBe("BARREN");
  });
});
