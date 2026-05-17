export type OnboardingIntent =
  | "find_first"
  | "scale"
  | "coach_agency"
  | "researching";

export type StrategyId =
  | "easy_win"
  | "cash_cow"
  | "blue_ocean"
  | "gbp_blitz"
  | "portfolio_builder"
  | "expand_conquer"
  | "seasonal_arbitrage";

export type OnboardingNextRoute = "/strategies" | "/explore" | "/agency";

export type OnboardingFocus =
  | "niche"
  | "value"
  | "process"
  | "ranking"
  | "diversify_city"
  | "replicate"
  | "revenue"
  | "emerging"
  | "agency"
  | "coaching"
  | "both";

export interface OnboardingStrategyRouting {
  starter: StrategyId;
  available: StrategyId[];
  rationale: string;
  next_route: OnboardingNextRoute;
}

export interface RouteOnboardingToStrategyArgs {
  intent?: OnboardingIntent | "";
  focus?: OnboardingFocus | null;
  coach_or_agency?: "coaching" | "agency" | "both" | null;
}

export type OnboardingProfileStatus =
  | "profile_started"
  | "profile_completed"
  | "strategy_recommended"
  | "target_selected"
  | "report_queued"
  | "cached_route_selected"
  | "upgrade_required"
  | "report_ready";

export type CoachOrAgency = "coaching" | "agency" | "both";

export interface OnboardingProfileRequest {
  intent: OnboardingIntent;
  focus?: OnboardingFocus | null;
  coach_or_agency?: CoachOrAgency | null;
  referral_source?: string | null;
}

export type OnboardingGeoScope = "city" | "state" | "region" | "nationwide";

export type OnboardingMetadataSource =
  | "typed"
  | "mapbox_selected"
  | "recent_history"
  | "fallback_cbsa";

export interface OnboardingTargetRequest {
  strategy_id: StrategyId;
  niche_keyword: string;
  geo_scope: OnboardingGeoScope;
  service_category_id?: string | null;
  city?: string | null;
  state?: string | null;
  cbsa_code?: string | null;
  place_id?: string | null;
  dataforseo_location_code?: number | null;
  resolved_label?: string | null;
  metadata_source?: OnboardingMetadataSource | null;
}
