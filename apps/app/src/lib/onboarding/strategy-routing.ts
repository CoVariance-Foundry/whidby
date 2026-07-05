import type {
  OnboardingStrategyRouting,
  RouteOnboardingToStrategyArgs,
} from "./types";
import { routeForOnboardingIntent } from "./segment-routing";

export function routeOnboardingToStrategy(
  args: RouteOnboardingToStrategyArgs,
): OnboardingStrategyRouting {
  const intent = args.intent || "";
  const focus = args.focus || args.coach_or_agency || "";

  if (intent === "find_first") {
    if (focus === "value") {
      return {
        starter: "easy_win",
        available: ["easy_win", "gbp_blitz", "keyword_hijack"],
        rationale:
          "You want to validate whether a market is worth building in. Easy Win gives you the simplest first scan before you branch into profile gaps or keyword checks.",
        next_route: routeForOnboardingIntent("find_first"),
      };
    }

    if (focus === "process") {
      return {
        starter: "easy_win",
        available: ["easy_win", "gbp_blitz", "keyword_hijack"],
        rationale:
          "You are new to the R&R process. Easy Win gives you the cleanest first data point: one city, one service, one score.",
        next_route: routeForOnboardingIntent("find_first"),
      };
    }

    if (focus === "ranking") {
      return {
        starter: "easy_win",
        available: ["easy_win", "gbp_blitz", "keyword_hijack"],
        rationale:
          "Learning how to rank is your block. Easy Win targets markets with weak competition so your first site can reach page 1.",
        next_route: routeForOnboardingIntent("find_first"),
      };
    }

    return {
      starter: "easy_win",
      available: ["easy_win", "gbp_blitz", "keyword_hijack"],
      rationale:
        "Picking the right niche is your block. Easy Win surfaces markets where competition is weakest: the fastest path to your first ranked site.",
      next_route: routeForOnboardingIntent("find_first"),
    };
  }

  if (intent === "scale") {
    if (focus === "diversify_city") {
      return {
        starter: "expand_conquer",
        available: [
          "expand_conquer",
          "easy_win",
          "gbp_blitz",
          "keyword_hijack",
          "portfolio_builder",
        ],
        rationale:
          "You want to add services in cities you already own. Expand & Conquer is the active path, with Portfolio Builder visible as a future node.",
        next_route: routeForOnboardingIntent("scale"),
      };
    }

    if (focus === "replicate") {
      return {
        starter: "expand_conquer",
        available: [
          "expand_conquer",
          "gbp_blitz",
          "easy_win",
          "keyword_hijack",
          "portfolio_builder",
        ],
        rationale:
          "You have a proven playbook. Expand & Conquer finds cities statistically similar to your success with equal-or-lower competition.",
        next_route: routeForOnboardingIntent("scale"),
      };
    }

    if (focus === "revenue") {
      return {
        starter: "expand_conquer",
        available: [
          "expand_conquer",
          "easy_win",
          "gbp_blitz",
          "keyword_hijack",
          "portfolio_builder",
        ],
        rationale:
          "You can rank. Expand & Conquer keeps the active path focused on repeatable markets while the heavier portfolio economics work stays deferred.",
        next_route: routeForOnboardingIntent("scale"),
      };
    }

    if (focus === "emerging") {
      return {
        starter: "keyword_hijack",
        available: [
          "keyword_hijack",
          "easy_win",
          "gbp_blitz",
          "portfolio_builder",
        ],
        rationale:
          "You want to stay ahead of the competition curve. Keyword Hijack is the side branch for focused keyword checks before spend.",
        next_route: routeForOnboardingIntent("scale"),
      };
    }

    return {
      starter: "expand_conquer",
      available: [
        "expand_conquer",
        "easy_win",
        "gbp_blitz",
        "keyword_hijack",
        "portfolio_builder",
      ],
      rationale:
        "With sites already ranked, Expand & Conquer helps you find the next repeatable market while deferred cross-metro plays stay out of the active path.",
      next_route: routeForOnboardingIntent("scale"),
    };
  }

  if (intent === "coach_agency") {
    if (focus === "agency") {
      return {
        starter: "easy_win",
        available: [
          "easy_win",
          "gbp_blitz",
          "expand_conquer",
          "keyword_hijack",
          "portfolio_builder",
        ],
        rationale:
          "Lead generation for clients routes to Agency, while the strategy path keeps the active catalog simple.",
        next_route: routeForOnboardingIntent("coach_agency"),
      };
    }

    if (focus === "coaching") {
      return {
        starter: "easy_win",
        available: [
          "easy_win",
          "gbp_blitz",
          "expand_conquer",
          "keyword_hijack",
          "portfolio_builder",
        ],
        rationale:
          "You teach R&R. Easy Win is where most students start, and the rest of the strategy set shows the progression.",
        next_route: routeForOnboardingIntent("coach_agency"),
      };
    }

    return {
      starter: "easy_win",
      available: [
        "easy_win",
        "gbp_blitz",
        "expand_conquer",
        "keyword_hijack",
        "portfolio_builder",
      ],
      rationale:
        "You do both teaching and client work. Start with Easy Win as the reference point while keeping every strategy available.",
      next_route: routeForOnboardingIntent("coach_agency"),
    };
  }

  if (intent === "researching") {
    return {
      starter: "easy_win",
      available: ["easy_win", "gbp_blitz", "keyword_hijack"],
      rationale:
        "You are exploring. Start in Explore Mode so you can browse cached data before spending scans.",
      next_route: routeForOnboardingIntent("researching"),
    };
  }

  return {
    starter: "easy_win",
    available: ["easy_win", "gbp_blitz", "keyword_hijack"],
    rationale: "",
    next_route: routeForOnboardingIntent("find_first"),
  };
}
