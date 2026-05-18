import { NextRequest, NextResponse } from "next/server";
import {
  EntitlementError,
  resolveEntitlementContext,
} from "@/lib/account/entitlements";
import type { OnboardingGeoScope, OnboardingProfileStatus } from "@/lib/onboarding/types";
import { createClient } from "@/lib/supabase/server";
import { POST as scoringPOST } from "../../agent/scoring/route";

type OnboardingTarget = {
  id: string;
  strategy_id: string;
  niche_keyword: string;
  geo_scope: OnboardingGeoScope;
  city: string | null;
  state: string | null;
  place_id: string | null;
  dataforseo_location_code: number | null;
  resolved_label: string | null;
  metadata_source: string | null;
};

class ValidationError extends Error {}

type SupabaseClient = Awaited<ReturnType<typeof createClient>>;

async function readStartRequest(req: NextRequest): Promise<{
  target_id?: string;
  strategy_id?: string;
}> {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return {};
  }

  if (body == null) return {};
  if (typeof body !== "object") {
    throw new ValidationError("Request body must be a JSON object when provided.");
  }

  const payload = body as Record<string, unknown>;
  if (payload.target_id != null && typeof payload.target_id !== "string") {
    throw new ValidationError("target_id must be a string when provided.");
  }
  if (payload.strategy_id != null && typeof payload.strategy_id !== "string") {
    throw new ValidationError("strategy_id must be a string when provided.");
  }

  return {
    target_id:
      payload.target_id && payload.target_id.trim()
        ? payload.target_id.trim()
        : undefined,
    strategy_id:
      payload.strategy_id && payload.strategy_id.trim()
        ? payload.strategy_id.trim()
        : undefined,
  };
}

function entitlementErrorResponse(error: EntitlementError) {
  return NextResponse.json(
    {
      status: "entitlement_error",
      code: error.code,
      message: error.message,
    },
    { status: error.status },
  );
}

async function updateProfileStatus(
  supabase: SupabaseClient,
  profileId: string,
  status: OnboardingProfileStatus,
  nextRoute: string,
) {
  const { error } = await supabase
    .from("onboarding_profiles")
    .update({
      status,
      next_route: nextRoute,
      updated_at: new Date().toISOString(),
      ...(status === "cached_route_selected" || status === "report_queued"
        ? { completed_at: new Date().toISOString() }
        : {}),
    })
    .eq("id", profileId);

  if (error) {
    throw new Error(`Failed to update onboarding status: ${error.message}`);
  }
}

function cachedRouteResponse(target: OnboardingTarget) {
  return NextResponse.json({
    status: "cached_route_selected",
    code: "broad_target_uses_cached_explore",
    message: "Broad onboarding targets use cached market discovery before fresh city scoring.",
    redirect_url: "/explore",
    target,
  });
}

function scoringRequest(req: NextRequest, target: OnboardingTarget) {
  const city = target.city || target.resolved_label;
  if (!city) {
    throw new ValidationError("City targets must include city or resolved_label before scoring.");
  }

  const headers = new Headers({ "Content-Type": "application/json" });
  const requestId = req.headers.get("x-request-id");
  if (requestId) headers.set("x-request-id", requestId);

  return new Request(new URL("/api/agent/scoring", req.url), {
    method: "POST",
    headers,
    body: JSON.stringify({
      city,
      service: target.niche_keyword,
      ...(target.state ? { state: target.state } : {}),
      ...(target.place_id ? { place_id: target.place_id } : {}),
      ...(typeof target.dataforseo_location_code === "number"
        ? { dataforseo_location_code: target.dataforseo_location_code }
        : {}),
      ...(target.metadata_source ? { metadata_source: target.metadata_source } : {}),
    }),
  });
}

export async function POST(req: NextRequest) {
  try {
    const supabase = await createClient();
    const { user, entitlement } = await resolveEntitlementContext(supabase);
    const body = await readStartRequest(req);

    const { data: profile, error: profileError } = await supabase
      .from("onboarding_profiles")
      .select("id")
      .eq("user_id", user.id)
      .maybeSingle();

    if (profileError) {
      return NextResponse.json(
        { status: "error", message: profileError.message },
        { status: 500 },
      );
    }

    if (!profile) {
      return NextResponse.json(
        {
          status: "not_found",
          message: "Onboarding profile was not found for the current user.",
        },
        { status: 404 },
      );
    }

    let targetQuery = supabase
      .from("onboarding_targets")
      .select("*")
      .eq("onboarding_profile_id", profile.id);

    if (body.target_id) {
      targetQuery = targetQuery.eq("id", body.target_id);
    }
    if (body.strategy_id) {
      targetQuery = targetQuery.eq("strategy_id", body.strategy_id);
    }

    const { data: target, error: targetError } = await targetQuery
      .order("updated_at", { ascending: false })
      .limit(1)
      .maybeSingle();

    if (targetError) {
      return NextResponse.json(
        { status: "error", message: targetError.message },
        { status: 500 },
      );
    }

    if (!target) {
      return NextResponse.json(
        {
          status: "not_found",
          message: "Onboarding target was not found for the current user.",
        },
        { status: 404 },
      );
    }

    if (target.geo_scope !== "city") {
      await updateProfileStatus(supabase, profile.id, "cached_route_selected", "/explore");
      return cachedRouteResponse(target);
    }

    if (
      !entitlement.fresh_report_quota_exempt &&
      entitlement.monthly_report_limit <= 0
    ) {
      await updateProfileStatus(supabase, profile.id, "upgrade_required", "/onboarding");
      return NextResponse.json(
        {
          status: "tier_limit",
          code: "fresh_reports_not_included",
          message: "Your current plan can browse cached reports but cannot generate fresh reports.",
          tier: entitlement.plan_key,
          monthly_report_limit: entitlement.monthly_report_limit,
        },
        { status: 403 },
      );
    }

    const scoringResponse = await scoringPOST(scoringRequest(req, target) as never);
    const scoring = await scoringResponse.json();

    if (!scoringResponse.ok) {
      return NextResponse.json(scoring, { status: scoringResponse.status });
    }

    const reportId = typeof scoring.report_id === "string" ? scoring.report_id : null;
    if (!reportId) {
      return NextResponse.json(
        {
          status: "error",
          message: "Scoring completed but did not return a report_id.",
          scoring,
        },
        { status: 502 },
      );
    }

    const redirectUrl = `/reports/${reportId}?generating=true`;
    await updateProfileStatus(supabase, profile.id, "report_queued", redirectUrl);

    return NextResponse.json({
      status: "success",
      report_id: reportId,
      redirect_url: redirectUrl,
      scoring,
    });
  } catch (error) {
    if (error instanceof EntitlementError) {
      return entitlementErrorResponse(error);
    }

    if (error instanceof ValidationError) {
      return NextResponse.json(
        { status: "validation_error", message: error.message },
        { status: 400 },
      );
    }

    console.error("[onboarding/start-report] POST failed", error);
    return NextResponse.json(
      {
        status: "error",
        message: error instanceof Error ? error.message : "Failed to start onboarding report.",
      },
      { status: 500 },
    );
  }
}
