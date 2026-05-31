import { NextRequest, NextResponse } from "next/server";
import {
  EntitlementError,
  resolveEntitlementContext,
} from "@/lib/account/entitlements";
import { createClient } from "@/lib/supabase/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const UPSTREAM_TIMEOUT_MS = 4_500;
const REPORT_SELECT =
  "id, created_at, spec_version, niche_keyword, geo_scope, geo_target, report_depth, strategy_profile, resolved_weights, keyword_expansion, metros, access_scope, owner_account_id" as const;

type RouteContext = {
  params: Promise<{ reportId: string }>;
};

type SupabaseReportRow = {
  id?: unknown;
  created_at?: unknown;
  spec_version?: unknown;
  niche_keyword?: unknown;
  geo_scope?: unknown;
  geo_target?: unknown;
  report_depth?: unknown;
  strategy_profile?: unknown;
  resolved_weights?: unknown;
  keyword_expansion?: unknown;
  metros?: unknown;
  access_scope?: unknown;
  owner_account_id?: unknown;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

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
    meta: null,
  };
}

function normalizeSupabaseReportRow(row: SupabaseReportRow) {
  return {
    id: typeof row.id === "string" ? row.id : "",
    created_at: typeof row.created_at === "string" ? row.created_at : "",
    spec_version: typeof row.spec_version === "string" ? row.spec_version : "1.1",
    niche_keyword: typeof row.niche_keyword === "string" ? row.niche_keyword : "",
    geo_scope: typeof row.geo_scope === "string" ? row.geo_scope : "city",
    geo_target: typeof row.geo_target === "string" ? row.geo_target : "",
    report_depth: typeof row.report_depth === "string" ? row.report_depth : "standard",
    strategy_profile:
      typeof row.strategy_profile === "string" ? row.strategy_profile : "balanced",
    resolved_weights: isRecord(row.resolved_weights)
      ? (row.resolved_weights as Record<string, number>)
      : null,
    keyword_expansion: isRecord(row.keyword_expansion) ? row.keyword_expansion : null,
    metros: Array.isArray(row.metros) ? row.metros : [],
    meta: null,
    access_scope: typeof row.access_scope === "string" ? row.access_scope : "account",
    owner_account_id:
      typeof row.owner_account_id === "string" ? row.owner_account_id : null,
  };
}

function withResolvedSpecVersion<T extends { spec_version: string }>(
  report: T,
  specVersion: string | null,
): T {
  if (!specVersion) return report;
  return { ...report, spec_version: specVersion };
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
      .select(REPORT_SELECT)
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

    const { data: v2Rows, error: v2Error } = await supabase
      .from("metro_score_v2")
      .select("spec_version")
      .eq("report_id", reportId)
      .limit(1);

    if (v2Error) {
      return NextResponse.json(
        {
          status: "unavailable",
          message: "Unable to verify report score version.",
          duration_ms: Date.now() - startedAt,
        },
        { status: 502 },
      );
    }

    const resolvedSpecVersion =
      Array.isArray(v2Rows) && typeof v2Rows[0]?.spec_version === "string"
        ? v2Rows[0].spec_version
        : null;

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);
    let upstream: Response;

    try {
      upstream = await fetch(`${API_BASE}/api/niches/${encodeURIComponent(reportId)}`, {
        cache: "no-store",
        signal: controller.signal,
      });
    } catch {
      return NextResponse.json({
        status: "success",
        report: withResolvedSpecVersion(
          normalizeSupabaseReportRow(reportAccess),
          resolvedSpecVersion,
        ),
        duration_ms: Date.now() - startedAt,
      });
    } finally {
      clearTimeout(timeout);
    }

    if (!upstream.ok) {
      return NextResponse.json({
        status: "success",
        report: withResolvedSpecVersion(
          normalizeSupabaseReportRow(reportAccess),
          resolvedSpecVersion,
        ),
        upstream_status: upstream.status,
        duration_ms: Date.now() - startedAt,
      });
    }

    try {
      const json = (await upstream.json()) as Record<string, unknown>;
      const report = normalizeReportPayload(json);
      return NextResponse.json({
        status: "success",
        report: withResolvedSpecVersion(report, resolvedSpecVersion),
        duration_ms: Date.now() - startedAt,
      });
    } catch {
      return NextResponse.json({
        status: "success",
        report: withResolvedSpecVersion(
          normalizeSupabaseReportRow(reportAccess),
          resolvedSpecVersion,
        ),
        duration_ms: Date.now() - startedAt,
      });
    }
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
