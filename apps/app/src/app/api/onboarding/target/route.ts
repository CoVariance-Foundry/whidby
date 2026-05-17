import { NextRequest, NextResponse } from "next/server";
import {
  EntitlementError,
  resolveEntitlementContext,
} from "@/lib/account/entitlements";
import type {
  OnboardingGeoScope,
  OnboardingMetadataSource,
  OnboardingTargetRequest,
  StrategyId,
} from "@/lib/onboarding/types";
import { createClient } from "@/lib/supabase/server";

const VALID_GEO_SCOPES: OnboardingGeoScope[] = [
  "city",
  "state",
  "region",
  "nationwide",
];

const VALID_STRATEGY_IDS: StrategyId[] = [
  "easy_win",
  "cash_cow",
  "blue_ocean",
  "gbp_blitz",
  "portfolio_builder",
  "expand_conquer",
  "seasonal_arbitrage",
];

const VALID_METADATA_SOURCES: OnboardingMetadataSource[] = [
  "typed",
  "mapbox_selected",
  "recent_history",
  "fallback_cbsa",
];

class ValidationError extends Error {}

function normalizeRequiredString(value: unknown, fieldName: string): string {
  if (typeof value !== "string" || !value.trim()) {
    throw new ValidationError(`${fieldName} is required.`);
  }
  return value.trim();
}

function normalizeOptionalString(value: unknown, fieldName: string): string | null {
  if (value == null) return null;
  if (typeof value !== "string") {
    throw new ValidationError(`${fieldName} must be a string when provided.`);
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function normalizeOptionalNumber(value: unknown, fieldName: string): number | null {
  if (value == null) return null;
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new ValidationError(`${fieldName} must be a number when provided.`);
  }
  return value;
}

function normalizeGeoScope(value: unknown): OnboardingGeoScope {
  if (typeof value !== "string" || !VALID_GEO_SCOPES.includes(value as OnboardingGeoScope)) {
    throw new ValidationError("geo_scope must be one of city, state, region, nationwide.");
  }
  return value as OnboardingGeoScope;
}

function normalizeStrategyId(value: unknown): StrategyId {
  const strategyId = normalizeRequiredString(value, "strategy_id");
  if (!VALID_STRATEGY_IDS.includes(strategyId as StrategyId)) {
    throw new ValidationError(
      "strategy_id must be one of easy_win, cash_cow, blue_ocean, gbp_blitz, portfolio_builder, expand_conquer, seasonal_arbitrage.",
    );
  }
  return strategyId as StrategyId;
}

function normalizeMetadataSource(value: unknown): OnboardingMetadataSource | null {
  if (value == null) return null;
  if (
    typeof value !== "string" ||
    !VALID_METADATA_SOURCES.includes(value as OnboardingMetadataSource)
  ) {
    throw new ValidationError(
      "metadata_source must be one of typed, mapbox_selected, recent_history, fallback_cbsa.",
    );
  }
  return value as OnboardingMetadataSource;
}

async function readTargetRequest(req: NextRequest): Promise<OnboardingTargetRequest> {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    throw new ValidationError("Request body must be valid JSON.");
  }

  if (!body || typeof body !== "object") {
    throw new ValidationError("Request body must be a JSON object.");
  }

  const payload = body as Record<string, unknown>;
  const geoScope = normalizeGeoScope(payload.geo_scope);
  const city = normalizeOptionalString(payload.city, "city");
  const resolvedLabel = normalizeOptionalString(payload.resolved_label, "resolved_label");

  if (geoScope === "city" && !city && !resolvedLabel) {
    throw new ValidationError("city targets must include city or resolved_label.");
  }

  return {
    strategy_id: normalizeStrategyId(payload.strategy_id),
    niche_keyword: normalizeRequiredString(payload.niche_keyword, "niche_keyword"),
    geo_scope: geoScope,
    service_category_id: normalizeOptionalString(
      payload.service_category_id,
      "service_category_id",
    ),
    city,
    state: normalizeOptionalString(payload.state, "state"),
    cbsa_code: normalizeOptionalString(payload.cbsa_code, "cbsa_code"),
    place_id: normalizeOptionalString(payload.place_id, "place_id"),
    dataforseo_location_code: normalizeOptionalNumber(
      payload.dataforseo_location_code,
      "dataforseo_location_code",
    ),
    resolved_label: resolvedLabel,
    metadata_source: normalizeMetadataSource(payload.metadata_source),
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

export async function POST(req: NextRequest) {
  try {
    const supabase = await createClient();
    const { user } = await resolveEntitlementContext(supabase);
    const body = await readTargetRequest(req);

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

    const { data: target, error: targetError } = await supabase
      .from("onboarding_targets")
      .upsert(
        {
          onboarding_profile_id: profile.id,
          strategy_id: body.strategy_id,
          niche_keyword: body.niche_keyword,
          service_category_id: body.service_category_id,
          geo_scope: body.geo_scope,
          city: body.city,
          state: body.state,
          cbsa_code: body.cbsa_code,
          place_id: body.place_id,
          dataforseo_location_code: body.dataforseo_location_code,
          resolved_label: body.resolved_label,
          metadata_source: body.metadata_source,
        },
        { onConflict: "onboarding_profile_id,strategy_id" },
      )
      .select()
      .single();

    if (targetError) {
      return NextResponse.json(
        { status: "error", message: targetError.message },
        { status: 500 },
      );
    }

    const { error: updateError } = await supabase
      .from("onboarding_profiles")
      .update({ status: "target_selected" })
      .eq("id", profile.id);

    if (updateError) {
      return NextResponse.json(
        { status: "error", message: updateError.message },
        { status: 500 },
      );
    }

    return NextResponse.json({ status: "success", target });
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

    console.error("[onboarding/target] POST failed", error);
    return NextResponse.json(
      {
        status: "error",
        message: error instanceof Error ? error.message : "Failed to save onboarding target.",
      },
      { status: 500 },
    );
  }
}
