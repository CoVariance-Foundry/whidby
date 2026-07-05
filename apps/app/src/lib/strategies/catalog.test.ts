import { describe, expect, it } from "vitest";
import { FALLBACK_STRATEGY_CATALOG, filterStrategyCatalog } from "./catalog";

describe("strategy catalog accents", () => {
  it("adds path and accent metadata to fallback catalog entries", () => {
    expect(
      FALLBACK_STRATEGY_CATALOG.strategies.map((strategy) => ({
        strategy_id: strategy.strategy_id,
        path_role: strategy.path_role,
        unlock: strategy.unlock_requirement?.requirement_id,
        runnable: strategy.is_runnable,
        accent_id: strategy.accent_id,
        text: strategy.accent?.text,
      })),
    ).toEqual([
      {
        strategy_id: "easy_win",
        path_role: "rail_step",
        unlock: "none",
        runnable: true,
        accent_id: "easy_win",
        text: "var(--strategy-easy-win)",
      },
      {
        strategy_id: "gbp_blitz",
        path_role: "rail_step",
        unlock: "scan_completed",
        runnable: true,
        accent_id: "gbp_blitz",
        text: "var(--strategy-gbp-blitz)",
      },
      {
        strategy_id: "expand_conquer",
        path_role: "rail_step",
        unlock: "ranked_site_declaration",
        runnable: true,
        accent_id: "expand_conquer",
        text: "var(--strategy-expand-conquer)",
      },
      {
        strategy_id: "keyword_hijack",
        path_role: "side_branch",
        unlock: "feasibility_preflight",
        runnable: true,
        accent_id: "keyword_hijack",
        text: "var(--strategy-keyword-hijack)",
      },
      {
        strategy_id: "portfolio_builder",
        path_role: "locked_teaser",
        unlock: "future_release",
        runnable: false,
        accent_id: "portfolio_builder",
        text: "var(--strategy-portfolio-builder)",
      },
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
      path_role: "rail_step",
      unlock_requirement: { requirement_id: "none" },
      accent_id: "easy_win",
      accent: { text: "var(--strategy-easy-win)" },
    });
  });

  it("filters deferred upstream strategies while preserving the locked Portfolio Builder teaser", () => {
    const catalog = filterStrategyCatalog({
      strategies: [
        {
          strategy_id: "cash_cow",
          name: "Cash Cow",
          description: "Old economics lens",
          status: "phase_2",
          input_shape: "cached_scan",
        },
        {
          strategy_id: "blue_ocean",
          name: "Blue Ocean",
          description: "Old emerging lens",
          status: "phase_2",
          input_shape: "cached_scan",
        },
        {
          strategy_id: "gbp_blitz",
          name: "Custom GBP Blitz",
          description: "Upstream copy",
          status: "launch",
          input_shape: "city_service",
        },
      ],
      global_modifiers: [],
    });

    expect(catalog.strategies.map((strategy) => strategy.strategy_id)).toEqual([
      "gbp_blitz",
      "portfolio_builder",
    ]);
    expect(catalog.strategies[0]).toMatchObject({
      strategy_id: "gbp_blitz",
      path_role: "rail_step",
      unlock_requirement: { requirement_id: "scan_completed" },
    });
    expect(catalog.strategies[1]).toMatchObject({
      strategy_id: "portfolio_builder",
      path_role: "locked_teaser",
      is_runnable: false,
    });
  });
});
