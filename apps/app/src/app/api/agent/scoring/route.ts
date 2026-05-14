import { NextRequest, NextResponse } from "next/server";
import { validateNicheQueryInput } from "@/lib/niche-finder/request-validation";
import type { FallbackPath, MetadataSource } from "@/lib/niche-finder/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function createRequestId() {
  return crypto.randomUUID();
}

function inferFallbackPath(payload: {
  state?: string;
  place_id?: string;
  dataforseo_location_code?: number;
}): FallbackPath {
  if (payload.place_id && typeof payload.dataforseo_location_code === "number") {
    return "canonical_targeting";
  }
  if (payload.state) return "city_state";
  return "city_only";
}

function normalizeMetadataSource(value: unknown): MetadataSource {
  const allowed: MetadataSource[] = [
    "typed",
    "mapbox_selected",
    "recent_history",
    "fallback_cbsa",
  ];
  if (typeof value === "string" && allowed.includes(value as MetadataSource)) {
    return value as MetadataSource;
  }
  return "typed";
}

export async function POST(req: NextRequest) {
  const proxyStart = Date.now();
  const requestId = req.headers.get("x-request-id") || createRequestId();
  try {
    const body = await req.json();
    const validation = validateNicheQueryInput(body);
    if (!validation.ok) {
      return NextResponse.json(
        { status: "validation_error", message: validation.message },
        { status: 400 },
      );
    }
    const dryRun = process.env.NEXT_PUBLIC_NICHE_DRY_RUN === "1";
    const normalizedCity = body.city.trim();
    const normalizedService = body.service.trim();
    const normalizedState =
      typeof body.state === "string" && body.state.trim() ? body.state.trim() : undefined;
    const normalizedPlaceId =
      typeof body.place_id === "string" && body.place_id.trim()
        ? body.place_id.trim()
        : undefined;
    const normalizedDfsCode =
      typeof body.dataforseo_location_code === "number"
        ? body.dataforseo_location_code
        : undefined;
    const metadataSource = normalizeMetadataSource(body.metadata_source);
    const fallbackPath = inferFallbackPath({
      state: normalizedState,
      place_id: normalizedPlaceId,
      dataforseo_location_code: normalizedDfsCode,
    });

    console.info(
      "[scoring-proxy] START request_id=%s city=%s service=%s metadata_source=%s fallback_path=%s dry_run=%s",
      requestId,
      normalizedCity,
      normalizedService,
      metadataSource,
      fallbackPath,
      dryRun,
    );

    const upstream = await fetch(`${API_BASE}/api/niches/score`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-request-id": requestId },
      body: JSON.stringify({
        niche: normalizedService,
        city: normalizedCity,
        ...(normalizedPlaceId ? { place_id: normalizedPlaceId } : {}),
        ...(typeof normalizedDfsCode === "number"
          ? { dataforseo_location_code: normalizedDfsCode }
          : {}),
        ...(normalizedState ? { state: normalizedState } : {}),
        metadata_source: metadataSource,
        strategy_profile: body.strategy_profile ?? "balanced",
        dry_run: dryRun,
      }),
    });

    const proxyMs = Date.now() - proxyStart;

    if (!upstream.ok) {
      const upstreamBody = await upstream.text();
      console.warn(
        "[scoring-proxy] FAIL request_id=%s upstream_status=%d proxy_ms=%d",
        requestId,
        upstream.status,
        proxyMs,
      );
      return NextResponse.json(
        {
          status: "unavailable",
          message: "Scoring engine did not return a result.",
          request_id: requestId,
          fallback_path: fallbackPath,
          upstream_status: upstream.status,
          upstream_body: upstreamBody.slice(0, 2000),
        },
        { status: 502 },
      );
    }

    const data = await upstream.json();
    const totalMs = Date.now() - proxyStart;
    console.info(
      "[scoring-proxy] DONE request_id=%s report_id=%s opportunity=%d fallback_path=%s upstream_ms=%d total_ms=%d",
      requestId,
      data.report_id,
      data.opportunity_score,
      fallbackPath,
      proxyMs,
      totalMs,
    );
    return NextResponse.json({
      query: {
        city: normalizedCity,
        service: normalizedService,
        ...(normalizedPlaceId ? { place_id: normalizedPlaceId } : {}),
        ...(typeof normalizedDfsCode === "number"
          ? { dataforseo_location_code: normalizedDfsCode }
          : {}),
        ...(normalizedState ? { state: normalizedState } : {}),
        metadata_source: metadataSource,
      },
      score_result: {
        opportunity_score: data.opportunity_score,
        classification_label: data.classification_label,
      },
      fallback_path: fallbackPath,
      request_id: requestId,
      report_id: data.report_id,
      entity_id: data.entity_id ?? null,
      snapshot_id: data.snapshot_id ?? null,
      persist_warning: data.persist_warning ?? null,
      status: "success",
    });
  } catch (err) {
    const proxyMs = Date.now() - proxyStart;
    console.error(
      "[scoring-proxy] ERROR request_id=%s proxy_ms=%d error=%s",
      requestId,
      proxyMs,
      err instanceof Error ? err.message : String(err),
    );
    return NextResponse.json(
      {
        status: "unavailable",
        message: "Failed to process scoring request.",
        request_id: requestId,
        error: err instanceof Error ? err.message : String(err),
      },
      { status: 502 },
    );
  }
}
