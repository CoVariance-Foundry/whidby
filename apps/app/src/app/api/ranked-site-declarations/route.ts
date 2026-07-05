import { NextRequest, NextResponse } from "next/server";
import {
  EntitlementError,
  resolveEntitlementContext,
} from "@/lib/account/entitlements";
import {
  isRankedSiteProofState,
  normalizeRankedSiteDomain,
  normalizeRankedSiteNiche,
  summarizeRankedSiteUnlock,
  type RankedSiteDeclaration,
} from "@/lib/strategies/ranked-site-declarations";
import { createClient } from "@/lib/supabase/server";

const DECLARATIONS_TABLE = "ranked_site_declarations";

class ValidationError extends Error {}

type JsonObject = Record<string, unknown>;

type QueryError = {
  message: string;
  code?: string;
};

function hasOwn(object: JsonObject, key: string): boolean {
  return Object.prototype.hasOwnProperty.call(object, key);
}

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

function normalizeState(value: unknown): string {
  const state = normalizeRequiredString(value, "state").toUpperCase();
  if (state.length < 2) {
    throw new ValidationError("state must include at least two characters.");
  }
  return state;
}

async function readJsonObject(req: NextRequest): Promise<JsonObject> {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    throw new ValidationError("Request body must be valid JSON.");
  }

  if (!body || typeof body !== "object" || Array.isArray(body)) {
    throw new ValidationError("Request body must be a JSON object.");
  }

  return body as JsonObject;
}

function metadataFromPayload(payload: JsonObject): Record<string, unknown> {
  const notes =
    normalizeOptionalString(payload.notes, "notes") ??
    (payload.metadata && typeof payload.metadata === "object" && !Array.isArray(payload.metadata)
      ? normalizeOptionalString((payload.metadata as JsonObject).notes, "metadata.notes")
      : null);

  return notes ? { notes } : {};
}

function normalizeDomainFromPayload(payload: JsonObject): {
  site_url: string | null;
  site_domain: string;
} {
  const siteUrl = normalizeOptionalString(payload.site_url, "site_url");
  const siteDomainInput =
    normalizeOptionalString(payload.site_domain, "site_domain") ?? siteUrl;

  if (!siteDomainInput) {
    throw new ValidationError("site_url or site_domain is required.");
  }

  const siteDomain = normalizeRankedSiteDomain(siteDomainInput);
  if (!siteDomain) {
    throw new ValidationError("site_url or site_domain must contain a valid domain.");
  }

  return {
    site_url: siteUrl,
    site_domain: siteDomain,
  };
}

function normalizeServiceFromPayload(payload: JsonObject): {
  niche_keyword: string;
  niche_normalized: string;
} {
  const nicheKeyword = normalizeRequiredString(
    payload.niche_keyword ?? payload.service ?? payload.niche,
    "niche_keyword",
  );

  return {
    niche_keyword: nicheKeyword,
    niche_normalized: normalizeRankedSiteNiche(nicheKeyword),
  };
}

function buildInsertPayload(payload: JsonObject, accountId: string, userId: string) {
  const domain = normalizeDomainFromPayload(payload);
  const service = normalizeServiceFromPayload(payload);

  return {
    account_id: accountId,
    created_by_user_id: userId,
    updated_by_user_id: userId,
    site_name: normalizeRequiredString(payload.site_name, "site_name"),
    ...domain,
    city: normalizeRequiredString(payload.city, "city"),
    state: normalizeState(payload.state),
    cbsa_code: normalizeOptionalString(payload.cbsa_code, "cbsa_code"),
    ...service,
    proof_state: "declared",
    active: true,
    metadata: metadataFromPayload(payload),
    declared_at: new Date().toISOString(),
    verified_at: null,
    deactivated_at: null,
  };
}

function buildPatchPayload(payload: JsonObject, userId: string) {
  const updates: JsonObject = {
    updated_by_user_id: userId,
  };

  if (hasOwn(payload, "site_name")) {
    updates.site_name = normalizeRequiredString(payload.site_name, "site_name");
  }

  if (hasOwn(payload, "site_url") || hasOwn(payload, "site_domain")) {
    Object.assign(updates, normalizeDomainFromPayload(payload));
  }

  if (hasOwn(payload, "city")) {
    updates.city = normalizeRequiredString(payload.city, "city");
  }

  if (hasOwn(payload, "state")) {
    updates.state = normalizeState(payload.state);
  }

  if (hasOwn(payload, "cbsa_code")) {
    updates.cbsa_code = normalizeOptionalString(payload.cbsa_code, "cbsa_code");
  }

  if (
    hasOwn(payload, "niche_keyword") ||
    hasOwn(payload, "service") ||
    hasOwn(payload, "niche")
  ) {
    Object.assign(updates, normalizeServiceFromPayload(payload));
  }

  if (hasOwn(payload, "notes") || hasOwn(payload, "metadata")) {
    updates.metadata = metadataFromPayload(payload);
  }

  if (hasOwn(payload, "proof_state")) {
    if (!isRankedSiteProofState(payload.proof_state)) {
      throw new ValidationError(
        "proof_state must be one of declared, verified, needs_review, rejected.",
      );
    }
    if (payload.proof_state !== "declared") {
      throw new ValidationError("proof_state can only be declared from this route.");
    }
    updates.proof_state = "declared";
    updates.verified_at = null;
  }

  if (hasOwn(payload, "active")) {
    if (typeof payload.active !== "boolean") {
      throw new ValidationError("active must be a boolean when provided.");
    }

    updates.active = payload.active;
    updates.deactivated_at = payload.active ? null : new Date().toISOString();
  }

  if (Object.keys(updates).length === 1) {
    throw new ValidationError("At least one ranked-site declaration field must be updated.");
  }

  return updates;
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

function queryErrorResponse(error: QueryError, fallback: string, status = 500) {
  return NextResponse.json(
    { status: "error", message: error.message || fallback },
    { status },
  );
}

async function loadDeclarations(supabase: Awaited<ReturnType<typeof createClient>>, accountId: string) {
  return supabase
    .from(DECLARATIONS_TABLE)
    .select("*")
    .eq("account_id", accountId)
    .order("updated_at", { ascending: false });
}

export async function GET() {
  try {
    const supabase = await createClient();
    const { entitlement } = await resolveEntitlementContext(supabase);
    const { data, error } = await loadDeclarations(supabase, entitlement.account_id);

    if (error) {
      return queryErrorResponse(error, "Failed to load ranked-site declarations.");
    }

    const declarations = (data ?? []) as RankedSiteDeclaration[];
    return NextResponse.json({
      status: "success",
      declarations,
      unlock: summarizeRankedSiteUnlock(declarations),
    });
  } catch (error) {
    if (error instanceof EntitlementError) {
      return entitlementErrorResponse(error);
    }

    console.error("[ranked-site-declarations] GET failed", error);
    return NextResponse.json(
      {
        status: "error",
        message:
          error instanceof Error ? error.message : "Failed to load ranked-site declarations.",
      },
      { status: 500 },
    );
  }
}

export async function POST(req: NextRequest) {
  try {
    const supabase = await createClient();
    const { user, entitlement } = await resolveEntitlementContext(supabase);
    const body = await readJsonObject(req);
    const insertPayload = buildInsertPayload(body, entitlement.account_id, user.id);

    const { data, error } = await supabase
      .from(DECLARATIONS_TABLE)
      .insert(insertPayload)
      .select()
      .single();

    if (error) {
      if (error.code === "23505") {
        return queryErrorResponse(
          error,
          "An active ranked-site declaration already exists for this site, city, and service.",
          409,
        );
      }
      return queryErrorResponse(error, "Failed to save ranked-site declaration.");
    }

    const declaration = data as RankedSiteDeclaration;
    return NextResponse.json({
      status: "success",
      declaration,
      unlock: summarizeRankedSiteUnlock([declaration]),
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

    console.error("[ranked-site-declarations] POST failed", error);
    return NextResponse.json(
      {
        status: "error",
        message:
          error instanceof Error ? error.message : "Failed to save ranked-site declaration.",
      },
      { status: 500 },
    );
  }
}

export async function PATCH(req: NextRequest) {
  try {
    const supabase = await createClient();
    const { user, entitlement } = await resolveEntitlementContext(supabase);
    const body = await readJsonObject(req);
    const id = normalizeRequiredString(body.id, "id");
    const patchPayload = buildPatchPayload(body, user.id);

    const { data: declaration, error: updateError } = await supabase
      .from(DECLARATIONS_TABLE)
      .update(patchPayload)
      .eq("id", id)
      .eq("account_id", entitlement.account_id)
      .select()
      .maybeSingle();

    if (updateError) {
      return queryErrorResponse(updateError, "Failed to update ranked-site declaration.");
    }

    if (!declaration) {
      return NextResponse.json(
        {
          status: "not_found",
          message: "Ranked-site declaration was not found for this account.",
        },
        { status: 404 },
      );
    }

    const { data: declarationsData, error: declarationsError } = await loadDeclarations(
      supabase,
      entitlement.account_id,
    );

    if (declarationsError) {
      return queryErrorResponse(
        declarationsError,
        "Ranked-site declaration was updated, but unlock state could not be refreshed.",
      );
    }

    const declarations = (declarationsData ?? []) as RankedSiteDeclaration[];
    return NextResponse.json({
      status: "success",
      declaration,
      unlock: summarizeRankedSiteUnlock(declarations),
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

    console.error("[ranked-site-declarations] PATCH failed", error);
    return NextResponse.json(
      {
        status: "error",
        message:
          error instanceof Error ? error.message : "Failed to update ranked-site declaration.",
      },
      { status: 500 },
    );
  }
}
