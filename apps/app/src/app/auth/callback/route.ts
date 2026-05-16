import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { isSafeNext } from "@/lib/auth/safe-next";
import type { OnboardingProfileStatus } from "@/lib/onboarding/types";

type OnboardingResumeProfile = {
  status: OnboardingProfileStatus;
  next_route: string | null;
};

const STORED_ROUTE_STATUSES: OnboardingProfileStatus[] = ["strategy_recommended"];

const INCOMPLETE_STATUSES: OnboardingProfileStatus[] = [
  "profile_started",
  "profile_completed",
];

function resolveSuccessPath(
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

  if (STORED_ROUTE_STATUSES.includes(profile.status)) {
    return isSafeNext(profile.next_route) ? profile.next_route : "/onboarding";
  }

  return "/reports";
}

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const nextParam = searchParams.get("next");
  const explicitSafeNext = isSafeNext(nextParam) ? nextParam : null;
  const frontendOrigin =
    process.env.NEXT_PUBLIC_APP_FRONTEND_URL?.replace(/\/$/, "") ?? origin;

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      const {
        data: { user },
        error: userError,
      } = await supabase.auth.getUser();

      if (userError || !user) {
        console.error("[auth/callback] getUser failed after session exchange", {
          message: userError?.message,
          status: userError?.status,
          code: userError?.code,
          name: userError?.name,
        });
        return NextResponse.redirect(
          `${frontendOrigin}/login?error=auth_callback_failed&reason=no_user`
        );
      }

      const { data: profile, error: profileError } = await supabase
        .from("onboarding_profiles")
        .select("status,next_route")
        .eq("user_id", user.id)
        .maybeSingle();

      if (profileError) {
        console.error("[auth/callback] onboarding profile lookup failed", {
          message: profileError.message,
        });
      }

      const next = resolveSuccessPath(
        explicitSafeNext,
        profileError ? null : (profile as OnboardingResumeProfile | null),
      );

      // resolveSuccessPath returns site-relative routes only: explicit/stored
      // routes are checked with isSafeNext and fallback routes are constants.
      return NextResponse.redirect(`${frontendOrigin}${next}`);
    }
    console.error("[auth/callback] exchangeCodeForSession failed", {
      message: error.message,
      status: error.status,
      code: error.code,
      name: error.name,
    });
    const reason = encodeURIComponent(error.code ?? error.message ?? "exchange_failed");
    return NextResponse.redirect(
      `${frontendOrigin}/login?error=auth_callback_failed&reason=${reason}`
    );
  }

  return NextResponse.redirect(
    `${frontendOrigin}/login?error=auth_callback_failed&reason=no_code`
  );
}
