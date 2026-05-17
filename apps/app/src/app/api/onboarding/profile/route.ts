import { NextRequest, NextResponse } from "next/server";
import {
  EntitlementError,
  resolveEntitlementContext,
} from "@/lib/account/entitlements";
import { routeOnboardingToStrategy } from "@/lib/onboarding/strategy-routing";
import type {
  CoachOrAgency,
  OnboardingFocus,
  OnboardingIntent,
  OnboardingProfileRequest,
} from "@/lib/onboarding/types";
import { createClient } from "@/lib/supabase/server";

const VALID_INTENTS: OnboardingIntent[] = [
  "find_first",
  "scale",
  "coach_agency",
  "researching",
];

const VALID_COACH_OR_AGENCY: CoachOrAgency[] = ["coaching", "agency", "both"];
const VALID_FOCUS: OnboardingFocus[] = [
  "niche",
  "value",
  "process",
  "ranking",
  "diversify_city",
  "replicate",
  "revenue",
  "emerging",
  "agency",
  "coaching",
  "both",
];

function isValidIntent(value: unknown): value is OnboardingIntent {
  return typeof value === "string" && VALID_INTENTS.includes(value as OnboardingIntent);
}

function normalizeOptionalString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function normalizeOptionalFocus(value: unknown): OnboardingFocus | null {
  if (value == null) return null;
  if (typeof value !== "string") {
    throw new ValidationError("focus must be a string when provided.");
  }

  const normalized = value.trim();
  if (!normalized) return null;
  if (!VALID_FOCUS.includes(normalized as OnboardingFocus)) {
    throw new ValidationError(
      "focus must be one of niche, value, process, ranking, diversify_city, replicate, revenue, emerging, agency, coaching, both.",
    );
  }
  return normalized as OnboardingFocus;
}

function normalizeOptionalTextField(value: unknown, fieldName: string): string | null {
  if (value == null) return null;
  if (typeof value !== "string") {
    throw new ValidationError(`${fieldName} must be a string when provided.`);
  }
  return normalizeOptionalString(value);
}

async function readProfileRequest(req: NextRequest): Promise<OnboardingProfileRequest> {
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
  if (!isValidIntent(payload.intent)) {
    throw new ValidationError("intent must be one of find_first, scale, coach_agency, researching.");
  }

  if (
    payload.coach_or_agency != null &&
    !VALID_COACH_OR_AGENCY.includes(payload.coach_or_agency as CoachOrAgency)
  ) {
    throw new ValidationError("coach_or_agency must be coaching, agency, or both.");
  }

  return {
    intent: payload.intent,
    focus: normalizeOptionalFocus(payload.focus),
    coach_or_agency: (payload.coach_or_agency as CoachOrAgency | null | undefined) ?? null,
    referral_source: normalizeOptionalTextField(payload.referral_source, "referral_source"),
  };
}

class ValidationError extends Error {}

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
    const { user, entitlement } = await resolveEntitlementContext(supabase);
    const body = await readProfileRequest(req);
    const routing = routeOnboardingToStrategy({
      intent: body.intent,
      focus: body.focus,
      coach_or_agency: body.coach_or_agency,
    });

    const { data, error } = await supabase
      .from("onboarding_profiles")
      .upsert(
        {
          user_id: user.id,
          account_id: entitlement.account_id,
          intent: body.intent,
          focus: body.focus,
          coach_or_agency: body.coach_or_agency,
          referral_source: body.referral_source,
          recommended_strategy_id: routing.starter,
          available_strategy_ids: routing.available,
          next_route: routing.next_route,
          status: "strategy_recommended",
          completed_at: new Date().toISOString(),
        },
        { onConflict: "user_id" },
      )
      .select()
      .single();

    if (error) {
      return NextResponse.json(
        { status: "error", message: error.message },
        { status: 500 },
      );
    }

    return NextResponse.json({ status: "success", profile: data, routing });
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

    console.error("[onboarding/profile] POST failed", error);
    return NextResponse.json(
      {
        status: "error",
        message: error instanceof Error ? error.message : "Failed to save onboarding profile.",
      },
      { status: 500 },
    );
  }
}

export async function GET() {
  try {
    const supabase = await createClient();
    const { user } = await resolveEntitlementContext(supabase);

    const { data: profile, error: profileError } = await supabase
      .from("onboarding_profiles")
      .select("*")
      .eq("user_id", user.id)
      .maybeSingle();

    if (profileError) {
      return NextResponse.json(
        { status: "error", message: profileError.message },
        { status: 500 },
      );
    }

    if (!profile) {
      return NextResponse.json({ status: "empty", profile: null, target: null });
    }

    const { data: target, error: targetError } = await supabase
      .from("onboarding_targets")
      .select("*")
      .eq("onboarding_profile_id", profile.id)
      .order("updated_at", { ascending: false })
      .limit(1)
      .maybeSingle();

    if (targetError) {
      return NextResponse.json(
        { status: "error", message: targetError.message },
        { status: 500 },
      );
    }

    return NextResponse.json({
      status: "success",
      profile,
      target: target ?? null,
    });
  } catch (error) {
    if (error instanceof EntitlementError) {
      return entitlementErrorResponse(error);
    }

    console.error("[onboarding/profile] GET failed", error);
    return NextResponse.json(
      {
        status: "error",
        message: error instanceof Error ? error.message : "Failed to load onboarding profile.",
      },
      { status: 500 },
    );
  }
}
