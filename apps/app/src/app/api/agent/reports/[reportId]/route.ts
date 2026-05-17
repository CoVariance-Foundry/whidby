import { NextRequest, NextResponse } from "next/server";
import {
  EntitlementError,
  resolveEntitlementContext,
} from "@/lib/account/entitlements";
import { createClient } from "@/lib/supabase/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const UPSTREAM_TIMEOUT_MS = 4_500;

type RouteContext = {
  params: Promise<{ reportId: string }>;
};

function normalizeReportPayload(payload: Record<string, unknown>) {
  const reportId = payload.report_id;
  const generatedAt = payload.generated_at;
  const specVersion = payload.spec_version;
  const input = payload.input as Record<string, unknown> | undefined;

  if (typeof reportId !== "string" || typeof generatedAt !== "string") {
    throw new Error("Upstream response missing required report fields.");
  }

  return {
    id: reportId,
    created_at: generatedAt,
    spec_version: typeof specVersion === "string" ? specVersion : "1.1",
    niche_keyword: typeof input?.niche_keyword === "string" ? input.niche_keyword : "",
    geo_scope: typeof input?.geo_scope === "string" ? input.geo_scope : "city",
    geo_target: typeof input?.geo_target === "string" ? input.geo_target : "",
    report_depth: typeof input?.report_depth === "string" ? input.report_depth : "standard",
    strategy_profile:
      typeof input?.strategy_profile === "string" ? input.strategy_profile : "balanced",
    resolved_weights: null,
    keyword_expansion:
      payload.keyword_expansion && typeof payload.keyword_expansion === "object"
        ? payload.keyword_expansion
        : null,
    metros: Array.isArray(payload.metros) ? payload.metros : [],
    meta: payload.meta && typeof payload.meta === "object" ? payload.meta : null,
  };
}

export async function GET(
  _req: NextRequest,
  { params }: RouteContext,
) {
  const { reportId } = await params;
  const startedAt = Date.now();

  if (!reportId) {
    return NextResponse.json(
      { status: "validation_error", message: "reportId is required." },
      { status: 400 },
    );
  }

  try {
    const supabase = await createClient();
    const { entitlement } = await resolveEntitlementContext(supabase);
    const { data: reportAccess, error: reportError } = await supabase
      .from("reports")
      .select("id, access_scope, owner_account_id")
      .eq("id", reportId)
      .maybeSingle();

    if (reportError) {
      return NextResponse.json(
        {
          status: "unavailable",
          message: "Unable to verify report access.",
          duration_ms: Date.now() - startedAt,
        },
        { status: 502 },
      );
    }

    if (!reportAccess) {
      return NextResponse.json(
        {
          status: "not_found",
          message: "Report not found.",
          duration_ms: Date.now() - startedAt,
        },
        { status: 404 },
      );
    }

    const accessScope = String(reportAccess.access_scope ?? "account");
    const ownerAccountId =
      typeof reportAccess.owner_account_id === "string"
        ? reportAccess.owner_account_id
        : null;
    const canReadReport =
      accessScope === "cached" || ownerAccountId === entitlement.account_id;

    if (!canReadReport) {
      return NextResponse.json(
        {
          status: "not_found",
          message: "Report not found.",
          duration_ms: Date.now() - startedAt,
        },
        { status: 404 },
      );
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);
    let upstream: Response;

    try {
      upstream = await fetch(`${API_BASE}/api/niches/${encodeURIComponent(reportId)}`, {
        cache: "no-store",
        signal: controller.signal,
      });
    } catch (error) {
      const isAbort = error instanceof DOMException && error.name === "AbortError";
      return NextResponse.json(
        {
          status: "unavailable",
          message: isAbort
            ? `Report upstream timed out after ${UPSTREAM_TIMEOUT_MS}ms.`
            : error instanceof Error
              ? error.message
              : "Failed to load report.",
          duration_ms: Date.now() - startedAt,
        },
        { status: 502 },
      );
    } finally {
      clearTimeout(timeout);
    }

    if (!upstream.ok) {
      return NextResponse.json(
        {
          status: "unavailable",
          message: "Failed to load report.",
          upstream_status: upstream.status,
          duration_ms: Date.now() - startedAt,
        },
        { status: 502 },
      );
    }

    const json = (await upstream.json()) as Record<string, unknown>;
    const report = normalizeReportPayload(json);
    return NextResponse.json({ status: "success", report, duration_ms: Date.now() - startedAt });
  } catch (error) {
    if (error instanceof EntitlementError) {
      return NextResponse.json(
        {
          status: "auth_error",
          code: error.code,
          message: error.message,
          duration_ms: Date.now() - startedAt,
        },
        { status: error.status },
      );
    }

    return NextResponse.json(
      {
        status: "unavailable",
        message: error instanceof Error ? error.message : "Failed to load report.",
        duration_ms: Date.now() - startedAt,
      },
      { status: 502 },
    );
  }
}
