import { describe, expect, it } from "vitest";
import {
  DEFAULT_AI_RESILIENCE_MODIFIER_STATE,
  filterAIResilienceFlagged,
  isAIResilienceScoreFlagged,
  normalizeAIResilienceModifierState,
  readAIResilienceScore,
  toAIResilienceFilterPayload,
} from "./ai-resilience-modifier";

describe("ai-resilience-modifier", () => {
  it("defaults to threshold 40 with hide flagged disabled", () => {
    expect(DEFAULT_AI_RESILIENCE_MODIFIER_STATE).toEqual({
      threshold: 40,
      hide_flagged: false,
    });
    expect(normalizeAIResilienceModifierState()).toEqual({
      threshold: 40,
      hide_flagged: false,
    });
  });

  it("flags only scores below the active threshold", () => {
    expect(isAIResilienceScoreFlagged(39, 40)).toBe(true);
    expect(isAIResilienceScoreFlagged(40, 40)).toBe(false);
    expect(isAIResilienceScoreFlagged(41, 40)).toBe(false);
    expect(isAIResilienceScoreFlagged(null, 40)).toBe(false);
  });

  it("filters flagged items only when hide_flagged is enabled", () => {
    const rows = [
      { id: "below", score: 22 },
      { id: "equal", score: 40 },
      { id: "missing", score: null },
    ];

    expect(
      filterAIResilienceFlagged(rows, (row) => row.score, {
        threshold: 40,
        hide_flagged: false,
      }),
    ).toEqual(rows);

    expect(
      filterAIResilienceFlagged(rows, (row) => row.score, {
        threshold: 40,
        hide_flagged: true,
      }).map((row) => row.id),
    ).toEqual(["equal", "missing"]);
  });

  it("maps hide_flagged to the existing snake_case upstream boolean", () => {
    expect(
      toAIResilienceFilterPayload({
        threshold: 55,
        hide_flagged: true,
      }),
    ).toEqual({ ai_resilience_filter: true });
  });

  it("reads AI Resilience scores from known result and report shapes", () => {
    expect(readAIResilienceScore({ ai_resilience_score: 33 })).toBe(33);
    expect(readAIResilienceScore({ scores: { ai_resilience: 44 } })).toBe(44);
    expect(readAIResilienceScore({ v2_scores: { ai_resilience: 55 } })).toBe(55);
    expect(readAIResilienceScore({ evidence: { ai_resilience_score: "66" } })).toBe(66);
    expect(readAIResilienceScore({ score: 99 })).toBeNull();
  });
});
