const LAUNCH_SAFE_RECOMMENDATIONS = new Set([
  "easy_win",
  "gbp_blitz",
  "keyword_hijack",
  "expand_conquer",
]);
const RECOMMENDATION_FALLBACK = "easy_win";

type OnboardingRecommendationSource = {
  profile?: { recommended_strategy_id?: string | null } | null;
  target?: { strategy_id?: string | null } | null;
};

export function resolveStrategyRecommendation({
  profile,
  target,
}: OnboardingRecommendationSource): string | undefined {
  const candidate = profile?.recommended_strategy_id ?? target?.strategy_id;
  if (!candidate) return undefined;
  return LAUNCH_SAFE_RECOMMENDATIONS.has(candidate) ? candidate : RECOMMENDATION_FALLBACK;
}
