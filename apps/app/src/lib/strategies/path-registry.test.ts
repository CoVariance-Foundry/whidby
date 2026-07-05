import { describe, expect, it } from "vitest";
import {
  getDeferredStrategyPathNodes,
  getRunnableStrategyPathNodes,
  getStrategyPathNode,
  getVisibleStrategyPathNodes,
  isUserFacingStrategyId,
} from "./path-registry";

describe("strategy path registry", () => {
  it("orders the visible production catalog around rail steps, side branch, and locked teaser", () => {
    expect(getVisibleStrategyPathNodes().map((node) => node.strategy_id)).toEqual([
      "easy_win",
      "gbp_blitz",
      "expand_conquer",
      "keyword_hijack",
      "portfolio_builder",
    ]);
    expect(getVisibleStrategyPathNodes().map((node) => node.path_role)).toEqual([
      "rail_step",
      "rail_step",
      "rail_step",
      "side_branch",
      "locked_teaser",
    ]);
  });

  it("captures unlock requirements for scan completion and ranked-site declaration", () => {
    expect(getStrategyPathNode("gbp_blitz")?.unlock_requirement.requirement_id).toBe(
      "scan_completed",
    );
    expect(getStrategyPathNode("expand_conquer")?.unlock_requirement.requirement_id).toBe(
      "ranked_site_declaration",
    );
    expect(getStrategyPathNode("keyword_hijack")?.unlock_requirement.requirement_id).toBe(
      "feasibility_preflight",
    );
  });

  it("keeps Portfolio Builder visible but not runnable", () => {
    expect(getStrategyPathNode("portfolio_builder")).toMatchObject({
      path_role: "locked_teaser",
      is_visible: true,
      is_runnable: false,
      status: "locked",
    });
    expect(getRunnableStrategyPathNodes().map((node) => node.strategy_id)).not.toContain(
      "portfolio_builder",
    );
  });

  it("keeps old cross-metro plays and balanced weighting out of user-facing catalog", () => {
    expect(getDeferredStrategyPathNodes().map((node) => node.strategy_id)).toEqual([
      "cash_cow",
      "blue_ocean",
      "seasonal_arbitrage",
    ]);
    expect(isUserFacingStrategyId("cash_cow")).toBe(false);
    expect(isUserFacingStrategyId("blue_ocean")).toBe(false);
    expect(isUserFacingStrategyId("seasonal_arbitrage")).toBe(false);
    expect(isUserFacingStrategyId("balanced")).toBe(false);
  });
});
