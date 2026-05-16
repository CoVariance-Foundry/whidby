import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  { params }: { params: { reportId: string } },
) {
  const { reportId } = params;
  const startedAt = Date.now();

  if (!reportId) {
    return NextResponse.json(
      { status: "validation_error", message: "reportId is required." },
      { status: 400 },
    );
  }

  try {
    const upstream = await fetch(`${API_BASE}/api/niches/${encodeURIComponent(reportId)}`);
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
