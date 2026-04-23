import { NextRequest, NextResponse } from "next/server";
import { validateNicheQueryInput } from "@/lib/niche-finder/request-validation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  const proxyStart = Date.now();
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

    console.info(
      "[scoring-proxy] START city=%s service=%s dry_run=%s",
      body.city,
      body.service,
      dryRun,
    );

    const upstream = await fetch(`${API_BASE}/api/niches/score`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        niche: body.service.trim(),
        city: body.city.trim(),
        ...(typeof body.place_id === "string" && body.place_id.trim()
          ? { place_id: body.place_id.trim() }
          : {}),
        ...(typeof body.dataforseo_location_code === "number"
          ? { dataforseo_location_code: body.dataforseo_location_code }
          : {}),
        ...(typeof body.state === "string" && body.state.trim()
          ? { state: body.state.trim() }
          : {}),
        strategy_profile: body.strategy_profile ?? "balanced",
        dry_run: dryRun,
      }),
    });

    const proxyMs = Date.now() - proxyStart;

    if (!upstream.ok) {
      const upstreamBody = await upstream.text();
      console.warn(
        "[scoring-proxy] FAIL upstream_status=%d proxy_ms=%d",
        upstream.status,
        proxyMs,
      );
      return NextResponse.json(
        {
          status: "unavailable",
          message: "Scoring engine did not return a result.",
          upstream_status: upstream.status,
          upstream_body: upstreamBody.slice(0, 2000),
        },
        { status: 502 },
      );
    }

    const data = await upstream.json();
    const totalMs = Date.now() - proxyStart;
    console.info(
      "[scoring-proxy] DONE report_id=%s opportunity=%d upstream_ms=%d total_ms=%d",
      data.report_id,
      data.opportunity_score,
      proxyMs,
      totalMs,
    );
    return NextResponse.json({
      query: {
        city: body.city.trim(),
        service: body.service.trim(),
        ...(typeof body.place_id === "string" && body.place_id.trim()
          ? { place_id: body.place_id.trim() }
          : {}),
        ...(typeof body.dataforseo_location_code === "number"
          ? { dataforseo_location_code: body.dataforseo_location_code }
          : {}),
        ...(typeof body.state === "string" && body.state.trim()
          ? { state: body.state.trim() }
          : {}),
      },
      score_result: {
        opportunity_score: data.opportunity_score,
        classification_label: data.classification_label,
      },
      report_id: data.report_id,
      entity_id: data.entity_id ?? null,
      snapshot_id: data.snapshot_id ?? null,
      persist_warning: data.persist_warning ?? null,
      status: "success",
    });
  } catch (err) {
    const proxyMs = Date.now() - proxyStart;
    console.error(
      "[scoring-proxy] ERROR proxy_ms=%d error=%s",
      proxyMs,
      err instanceof Error ? err.message : String(err),
    );
    return NextResponse.json(
      {
        status: "unavailable",
        message: "Failed to process scoring request.",
        error: err instanceof Error ? err.message : String(err),
      },
      { status: 502 },
    );
  }
}
