import { describe, expect, it } from "vitest";
import { FALLBACK_STRATEGY_CATALOG, filterStrategyCatalog } from "./catalog";

describe("strategy catalog accents", () => {
  it("adds accent metadata to fallback catalog entries", () => {
    expect(
      FALLBACK_STRATEGY_CATALOG.strategies.map((strategy) => ({
        strategy_id: strategy.strategy_id,
        accent_id: strategy.accent_id,
        text: strategy.accent?.text,
      })),
    ).toEqual([
      { strategy_id: "easy_win", accent_id: "easy_win", text: "var(--strategy-easy-win)" },
      { strategy_id: "gbp_blitz", accent_id: "gbp_blitz", text: "var(--strategy-gbp-blitz)" },
      {
        strategy_id: "keyword_hijack",
        accent_id: "keyword_hijack",
        text: "var(--strategy-keyword-hijack)",
      },
      {
        strategy_id: "expand_conquer",
        accent_id: "expand_conquer",
        text: "var(--strategy-expand-conquer)",
      },
      { strategy_id: "cash_cow", accent_id: "cash_cow", text: "var(--strategy-cash-cow)" },
    ]);
  });

  it("preserves upstream fields while hydrating missing accent metadata", () => {
    const catalog = filterStrategyCatalog({
      strategies: [
        {
          strategy_id: "easy_win",
          name: "Custom easy win",
          description: "Upstream copy",
          status: "launch",
          input_shape: "city_service",
        },
      ],
      global_modifiers: [],
    });

    expect(catalog.strategies[0]).toMatchObject({
      strategy_id: "easy_win",
      name: "Custom easy win",
      accent_id: "easy_win",
      accent: { text: "var(--strategy-easy-win)" },
    });
  });
});

