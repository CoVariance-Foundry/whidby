import type { OnboardingIntent, OnboardingNextRoute } from "./types";

export type SegmentRouteSource =
  | "intent"
  | "report_history"
  | "stored_route"
  | "default";

export interface SegmentRoutingProfile {
  intent?: OnboardingIntent | string | null;
  next_route?: string | null;
}

export interface SegmentRoutingReportHistory {
  completed_report_count?: number | null;
  has_ranked_site_declaration?: boolean | null;
}

export interface OnboardingSegmentRouteResolution {
  segment: OnboardingIntent;
  route: OnboardingNextRoute;
  source: SegmentRouteSource;
}

export interface ResolveOnboardingSegmentRouteArgs {
  profile?: SegmentRoutingProfile | null;
  report_history?: SegmentRoutingReportHistory | null;
}

const ROUTE_BY_INTENT: Record<OnboardingIntent, OnboardingNextRoute> = {
  find_first: "/",
  scale: "/strategies",
  coach_agency: "/agency",
  researching: "/explore",
};

const SEGMENT_BY_ROUTE: Record<OnboardingNextRoute, OnboardingIntent> = {
  "/": "find_first",
  "/strategies": "scale",
  "/agency": "coach_agency",
  "/explore": "researching",
};

const ONBOARDING_INTENTS = new Set<string>(Object.keys(ROUTE_BY_INTENT));
const ONBOARDING_NEXT_ROUTES = new Set<string>(Object.keys(SEGMENT_BY_ROUTE));

export function isOnboardingIntent(value: unknown): value is OnboardingIntent {
  return typeof value === "string" && ONBOARDING_INTENTS.has(value);
}

export function isOnboardingNextRoute(value: unknown): value is OnboardingNextRoute {
  return typeof value === "string" && ONBOARDING_NEXT_ROUTES.has(value);
}

export function routeForOnboardingIntent(
  intent: OnboardingIntent | null | undefined,
): OnboardingNextRoute {
  return intent ? ROUTE_BY_INTENT[intent] : "/";
}

function reportHistorySegment(
  reportHistory: SegmentRoutingReportHistory | null | undefined,
): OnboardingIntent | null {
  if (!reportHistory) return null;
  if (reportHistory.has_ranked_site_declaration) return "scale";
  if ((reportHistory.completed_report_count ?? 0) > 0) return "scale";
  return null;
}

export function resolveOnboardingSegmentRoute(
  args: ResolveOnboardingSegmentRouteArgs = {},
): OnboardingSegmentRouteResolution {
  const intent = args.profile?.intent;
  if (isOnboardingIntent(intent)) {
    return {
      segment: intent,
      route: routeForOnboardingIntent(intent),
      source: "intent",
    };
  }

  const historySegment = reportHistorySegment(args.report_history);
  if (historySegment) {
    return {
      segment: historySegment,
      route: routeForOnboardingIntent(historySegment),
      source: "report_history",
    };
  }

  const storedRoute = args.profile?.next_route;
  if (isOnboardingNextRoute(storedRoute)) {
    return {
      segment: SEGMENT_BY_ROUTE[storedRoute],
      route: storedRoute,
      source: "stored_route",
    };
  }

  return {
    segment: "find_first",
    route: "/",
    source: "default",
  };
}
