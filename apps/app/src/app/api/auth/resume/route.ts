import { NextResponse } from "next/server";
import { isSafeNext } from "@/lib/auth/safe-next";
import { resolveOnboardingSegmentRoute } from "@/lib/onboarding/segment-routing";
import type { OnboardingProfileStatus } from "@/lib/onboarding/types";
import { createClient } from "@/lib/supabase/server";

type OnboardingResumeProfile = {
  status: OnboardingProfileStatus;
  next_route: string | null;
  intent: string | null;
};

const SEGMENT_ROUTE_STATUSES: OnboardingProfileStatus[] = [
  "strategy_recommended",
];

const INCOMPLETE_STATUSES: OnboardingProfileStatus[] = [
  "profile_started",
  "profile_completed",
];

function resolveResumePath(
  explicitSafeNext: string | null,
  profile: OnboardingResumeProfile | null,
) {
  if (explicitSafeNext) {
    return explicitSafeNext;
  }

  if (!profile || INCOMPLETE_STATUSES.includes(profile.status)) {
    return "/onboarding";
  }

  if (profile.status === "target_selected") {
    return "/onboarding";
  }

  if (profile.status === "cached_route_selected") {
    return isSafeNext(profile.next_route) ? profile.next_route : "/onboarding";
  }

  if (SEGMENT_ROUTE_STATUSES.includes(profile.status)) {
    const { route } = resolveOnboardingSegmentRoute({ profile });
    return isSafeNext(route) ? route : "/onboarding";
  }

  return "/reports";
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const explicitSafeNext = isSafeNext(searchParams.get("next"))
    ? searchParams.get("next")
    : null;

  const supabase = await createClient();
  const {
    data: { user },
    error: userError,
  } = await supabase.auth.getUser();

  if (userError || !user) {
    return NextResponse.json(
      { status: "error", next: "/login" },
      { status: 401 },
    );
  }

  const { data: profile, error: profileError } = await supabase
    .from("onboarding_profiles")
    .select("status,next_route,intent")
    .eq("user_id", user.id)
    .maybeSingle();

  if (profileError) {
    console.error("[auth/resume] onboarding profile lookup failed", {
      message: profileError.message,
    });
  }

  return NextResponse.json({
    status: "success",
    next: resolveResumePath(
      explicitSafeNext,
      profileError ? null : (profile as OnboardingResumeProfile | null),
    ),
  });
}
