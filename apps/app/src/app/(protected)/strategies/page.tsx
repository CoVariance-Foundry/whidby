import { loadStrategyCatalog } from "@/lib/strategies/catalog";
import { resolveStrategyRecommendation } from "@/lib/strategies/recommendation";
import { createClient } from "@/lib/supabase/server";
import StrategiesGalleryClient from "./StrategiesGalleryClient";

export const dynamic = "force-dynamic";

async function loadOnboardingRecommendation() {
  try {
    const supabase = await createClient();
    const {
      data: { user },
      error: userError,
    } = await supabase.auth.getUser();

    if (userError || !user) return undefined;

    const { data: profile, error: profileError } = await supabase
      .from("onboarding_profiles")
      .select("id,recommended_strategy_id")
      .eq("user_id", user.id)
      .maybeSingle();

    if (profileError || !profile) return undefined;

    const { data: target, error: targetError } = await supabase
      .from("onboarding_targets")
      .select("strategy_id")
      .eq("onboarding_profile_id", profile.id)
      .order("updated_at", { ascending: false })
      .limit(1)
      .maybeSingle();

    if (targetError) return undefined;

    return resolveStrategyRecommendation({ profile, target });
  } catch {
    return undefined;
  }
}

export default async function StrategiesPage() {
  const catalog = await loadStrategyCatalog();
  const recommendedStrategyId = await loadOnboardingRecommendation();

  return (
    <main
      className="page"
      style={{
        maxWidth: 1280,
        margin: "0 auto",
        width: "100%",
      }}
    >
      <StrategiesGalleryClient
        catalog={catalog}
        recommendedStrategyId={recommendedStrategyId}
        recommendationReason="your onboarding route points to this lens"
      />
    </main>
  );
}
