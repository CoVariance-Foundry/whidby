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
      starter: "cash_cow",
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
      next_route: "/strategies",
    });
  });

  it("routes first-value users to Cash Cow", () => {
    expect(
      routeOnboardingToStrategy({
        intent: "find_first",
        focus: "value",
      }),
    ).toMatchObject({
      starter: "cash_cow",
      next_route: "/strategies",
    });
  });

  it("routes city diversification to Portfolio Builder", () => {
    expect(
      routeOnboardingToStrategy({
        intent: "scale",
        focus: "diversify_city",
      }),
    ).toMatchObject({
      starter: "portfolio_builder",
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

  it("routes scale revenue focus to Cash Cow", () => {
    expect(
      routeOnboardingToStrategy({
        intent: "scale",
        focus: "revenue",
      }),
    ).toMatchObject({
      starter: "cash_cow",
      next_route: "/strategies",
    });
  });

  it("routes scale emerging focus to Blue Ocean", () => {
    expect(
      routeOnboardingToStrategy({
        intent: "scale",
        focus: "emerging",
      }),
    ).toMatchObject({
      starter: "blue_ocean",
      next_route: "/strategies",
    });
  });

  it("routes scale users without a focus to Cash Cow", () => {
    expect(routeOnboardingToStrategy({ intent: "scale" })).toMatchObject({
      starter: "cash_cow",
      next_route: "/strategies",
    });
  });

  it("routes coaching-focused users to Easy Win", () => {
    expect(
      routeOnboardingToStrategy({
        intent: "coach_agency",
        focus: "coaching",
      }),
    ).toMatchObject({
      starter: "easy_win",
      next_route: "/strategies",
    });
  });

  it("routes coach or agency users without a focus to Easy Win", () => {
    expect(routeOnboardingToStrategy({ intent: "coach_agency" })).toMatchObject({
      starter: "easy_win",
      next_route: "/strategies",
    });
  });
});
