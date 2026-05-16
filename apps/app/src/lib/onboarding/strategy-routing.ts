import type {
  OnboardingStrategyRouting,
  RouteOnboardingToStrategyArgs,
} from "./types";

export function routeOnboardingToStrategy(
  args: RouteOnboardingToStrategyArgs,
): OnboardingStrategyRouting {
  const intent = args.intent || "";
  const focus = args.focus || args.coach_or_agency || "";

  if (intent === "find_first") {
    if (focus === "value") {
      return {
        starter: "cash_cow",
        available: ["easy_win", "cash_cow", "blue_ocean", "gbp_blitz"],
        rationale:
          "You want to validate whether a market is worth building in. Cash Cow shows you what each lead is worth before you commit.",
        next_route: "/strategies",
      };
    }

    if (focus === "process") {
      return {
        starter: "easy_win",
        available: ["easy_win", "gbp_blitz", "cash_cow", "blue_ocean"],
        rationale:
          "You are new to the R&R process. Easy Win gives you the cleanest first data point: one city, one service, one score.",
        next_route: "/strategies",
      };
    }

    if (focus === "ranking") {
      return {
        starter: "easy_win",
        available: ["easy_win", "gbp_blitz", "cash_cow", "blue_ocean"],
        rationale:
          "Learning how to rank is your block. Easy Win targets markets with weak competition so your first site can reach page 1.",
        next_route: "/strategies",
      };
    }

    return {
      starter: "easy_win",
      available: ["easy_win", "cash_cow", "blue_ocean", "gbp_blitz"],
      rationale:
        "Picking the right niche is your block. Easy Win surfaces markets where competition is weakest: the fastest path to your first ranked site.",
      next_route: "/strategies",
    };
  }

  if (intent === "scale") {
    if (focus === "diversify_city") {
      return {
        starter: "portfolio_builder",
        available: [
          "portfolio_builder",
          "expand_conquer",
          "cash_cow",
          "blue_ocean",
          "easy_win",
        ],
        rationale:
          "You want to add services in cities you already own. Portfolio Builder finds adjacent categories so you diversify without cannibalizing.",
        next_route: "/strategies",
      };
    }

    if (focus === "replicate") {
      return {
        starter: "expand_conquer",
        available: [
          "expand_conquer",
          "portfolio_builder",
          "cash_cow",
          "seasonal_arbitrage",
        ],
        rationale:
          "You have a proven playbook. Expand & Conquer finds cities statistically similar to your success with equal-or-lower competition.",
        next_route: "/strategies",
      };
    }

    if (focus === "revenue") {
      return {
        starter: "cash_cow",
        available: [
          "cash_cow",
          "portfolio_builder",
          "expand_conquer",
          "easy_win",
          "blue_ocean",
        ],
        rationale:
          "You can rank. Now you want higher-value leads. Cash Cow ranks markets by revenue and demand signals.",
        next_route: "/strategies",
      };
    }

    if (focus === "emerging") {
      return {
        starter: "blue_ocean",
        available: [
          "blue_ocean",
          "cash_cow",
          "expand_conquer",
          "portfolio_builder",
        ],
        rationale:
          "You want to stay ahead of the competition curve. Blue Ocean surfaces categories with rising demand but empty SERPs.",
        next_route: "/strategies",
      };
    }

    return {
      starter: "cash_cow",
      available: [
        "cash_cow",
        "portfolio_builder",
        "expand_conquer",
        "blue_ocean",
        "easy_win",
      ],
      rationale:
        "With sites already ranked, Cash Cow helps you pick the next highest-value market to add.",
      next_route: "/strategies",
    };
  }

  if (intent === "coach_agency") {
    if (focus === "agency") {
      return {
        starter: "cash_cow",
        available: [
          "cash_cow",
          "expand_conquer",
          "portfolio_builder",
          "blue_ocean",
          "gbp_blitz",
          "easy_win",
          "seasonal_arbitrage",
        ],
        rationale:
          "Lead generation for clients means Cash Cow plus multi-market analysis is your primary workflow for qualifying territories at scale.",
        next_route: "/agency",
      };
    }

    if (focus === "coaching") {
      return {
        starter: "easy_win",
        available: [
          "easy_win",
          "cash_cow",
          "blue_ocean",
          "gbp_blitz",
          "portfolio_builder",
          "expand_conquer",
          "seasonal_arbitrage",
        ],
        rationale:
          "You teach R&R. Easy Win is where most students start, and the rest of the strategy set shows the progression.",
        next_route: "/strategies",
      };
    }

    return {
      starter: "easy_win",
      available: [
        "easy_win",
        "cash_cow",
        "blue_ocean",
        "gbp_blitz",
        "portfolio_builder",
        "expand_conquer",
        "seasonal_arbitrage",
      ],
      rationale:
        "You do both teaching and client work. Start with Easy Win as the reference point while keeping every strategy available.",
      next_route: "/strategies",
    };
  }

  if (intent === "researching") {
    return {
      starter: "easy_win",
      available: ["easy_win", "cash_cow", "blue_ocean", "gbp_blitz"],
      rationale:
        "You are exploring. Start in Explore Mode so you can browse cached data before spending scans.",
      next_route: "/explore",
    };
  }

  return {
    starter: "easy_win",
    available: ["easy_win", "cash_cow", "blue_ocean", "gbp_blitz"],
    rationale: "",
    next_route: "/strategies",
  };
}
