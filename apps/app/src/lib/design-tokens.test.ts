import { describe, expect, it } from "vitest";
import { scoreToneForValue, strategyAccentForId } from "./design-tokens";

describe("scoreToneForValue", () => {
  it.each([
    [80, "high", "var(--score-high)"],
    [60, "good", "var(--score-good)"],
    [40, "warning", "var(--score-warning)"],
    [39.99, "danger", "var(--score-danger)"],
  ])("maps %s to the %s score tone", (value, key, text) => {
    expect(scoreToneForValue(value)).toMatchObject({ key, text, bar: text });
  });

  it("returns a muted token set for missing or invalid scores", () => {
    expect(scoreToneForValue(null)).toMatchObject({
      key: "muted",
      text: "var(--score-muted)",
    });
    expect(scoreToneForValue(Number.NaN)).toMatchObject({
      key: "muted",
      text: "var(--score-muted)",
    });
  });
});

describe("strategyAccentForId", () => {
  it("maps known strategy ids to CSS variable token sets", () => {
    expect(strategyAccentForId("gbp_blitz")).toMatchObject({
      accent_id: "gbp_blitz",
      text: "var(--strategy-gbp-blitz)",
      background: "var(--strategy-gbp-blitz-soft)",
      border: "var(--strategy-gbp-blitz-border)",
    });
  });

  it("keeps keyword_hijack on the emerald fallback accent", () => {
    expect(strategyAccentForId("keyword_hijack")).toMatchObject({
      accent_id: "keyword_hijack",
      text: "var(--strategy-keyword-hijack)",
    });
  });

  it("falls back to easy_win for unknown or missing strategy ids", () => {
    expect(strategyAccentForId("unknown_strategy")).toMatchObject({
      accent_id: "easy_win",
      text: "var(--strategy-easy-win)",
    });
    expect(strategyAccentForId(undefined)).toMatchObject({
      accent_id: "easy_win",
      text: "var(--strategy-easy-win)",
    });
  });
});

