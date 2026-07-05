import { describe, expect, it } from "vitest";
import { routeOnboardingToStrategy } from "./strategy-routing";

describe("routeOnboardingToStrategy", () => {
  it("routes researching users to Explore", () => {
    expect(routeOnboardingToStrategy({ intent: "researching" })).toMatchObject({
      starter: "easy_win",
      next_route: "/explore",
    });
  });

  it("routes agency-focused users to Multi-market", () => {
    expect(
      routeOnboardingToStrategy({
        intent: "coach_agency",
        focus: "agency",
      }),
    ).toMatchObject({
      starter: "easy_win",
      next_route: "/agency",
    });
  });

  it("routes first-niche users to Easy Win by default", () => {
    expect(
      routeOnboardingToStrategy({
        intent: "find_first",
        focus: "niche",
      }),
    ).toMatchObject({
      starter: "easy_win",
      next_route: "/",
    });
  });

  it("routes first-value users to Easy Win", () => {
    expect(
      routeOnboardingToStrategy({
        intent: "find_first",
        focus: "value",
      }),
    ).toMatchObject({
      starter: "easy_win",
      next_route: "/",
    });
  });

  it("routes city diversification to Expand & Conquer while keeping Portfolio Builder visible", () => {
    expect(
      routeOnboardingToStrategy({
        intent: "scale",
        focus: "diversify_city",
      }),
    ).toMatchObject({
      starter: "expand_conquer",
      available: expect.arrayContaining(["portfolio_builder"]),
      next_route: "/strategies",
    });
  });

  it("routes replication to Expand & Conquer", () => {
    expect(
      routeOnboardingToStrategy({
        intent: "scale",
        focus: "replicate",
      }),
    ).toMatchObject({
      starter: "expand_conquer",
      next_route: "/strategies",
    });
  });

  it("routes scale revenue focus to Expand & Conquer", () => {
    expect(
      routeOnboardingToStrategy({
        intent: "scale",
        focus: "revenue",
      }),
    ).toMatchObject({
      starter: "expand_conquer",
      next_route: "/strategies",
    });
  });

  it("routes scale emerging focus to Keyword Hijack", () => {
    expect(
      routeOnboardingToStrategy({
        intent: "scale",
        focus: "emerging",
      }),
    ).toMatchObject({
      starter: "keyword_hijack",
      next_route: "/strategies",
    });
  });

  it("routes scale users without a focus to Expand & Conquer", () => {
    expect(routeOnboardingToStrategy({ intent: "scale" })).toMatchObject({
      starter: "expand_conquer",
      next_route: "/strategies",
    });
  });

  it("does not recommend deferred cross-metro strategies", () => {
    const routes = [
      routeOnboardingToStrategy({ intent: "find_first", focus: "value" }),
      routeOnboardingToStrategy({ intent: "scale", focus: "revenue" }),
      routeOnboardingToStrategy({ intent: "scale", focus: "emerging" }),
      routeOnboardingToStrategy({ intent: "coach_agency", focus: "agency" }),
    ];

    for (const routing of routes) {
      expect([routing.starter, ...routing.available]).not.toEqual(
        expect.arrayContaining(["cash_cow", "blue_ocean", "seasonal_arbitrage"]),
      );
    }
  });

  it("routes coaching-focused users to Easy Win", () => {
    expect(
      routeOnboardingToStrategy({
        intent: "coach_agency",
        focus: "coaching",
      }),
    ).toMatchObject({
      starter: "easy_win",
      next_route: "/agency",
    });
  });

  it("routes coach or agency users without a focus to Easy Win", () => {
    expect(routeOnboardingToStrategy({ intent: "coach_agency" })).toMatchObject({
      starter: "easy_win",
      next_route: "/agency",
    });
  });
});
