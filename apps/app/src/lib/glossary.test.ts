import { describe, expect, it } from "vitest";
import {
  GLOSSARY_TERM_KEYS,
  GLOSSARY_TERMS,
  getGlossaryTerm,
  resolveGlossaryTerm,
} from "@/lib/glossary";

describe("glossary lookup", () => {
  it("defines the initial WHI-149 term set once", () => {
    expect(GLOSSARY_TERMS.map((term) => term.key)).toEqual(GLOSSARY_TERM_KEYS);
    expect(GLOSSARY_TERMS).toHaveLength(9);
  });

  it("looks up terms by key, label, and aliases", () => {
    expect(getGlossaryTerm("ai_resilience")?.label).toBe("AI Resilience");
    expect(getGlossaryTerm("Keyword Difficulty / KD")?.key).toBe("keyword_difficulty");
    expect(getGlossaryTerm("KD")?.label).toBe("Keyword Difficulty / KD");
    expect(getGlossaryTerm("local pack")?.key).toBe("map_pack");
    expect(getGlossaryTerm("ranked-site declaration")?.key).toBe("ranked_site");
  });

  it("returns undefined for unknown terms", () => {
    expect(getGlossaryTerm("source confidence")).toBeUndefined();
  });

  it("resolves unknown terms with a caller-provided fallback", () => {
    expect(
      resolveGlossaryTerm("source confidence", {
        label: "Source confidence",
        definition: "How much evidence is available for this market.",
      }),
    ).toEqual({
      key: "fallback",
      label: "Source confidence",
      definition: "How much evidence is available for this market.",
      context: undefined,
      isFallback: true,
    });
  });
});
