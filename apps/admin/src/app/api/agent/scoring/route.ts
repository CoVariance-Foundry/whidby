import { NextRequest, NextResponse } from "next/server";
import { validateNicheQueryInput } from "@/lib/niche-finder/request-validation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
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

    const upstream = await fetch(`${API_BASE}/api/niches/score`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        niche: body.service.trim(),
        city: body.city.trim(),
        // state is optional — omitted lets the backend search all seeded
        // metros. Only pass when the caller explicitly sets it.
        ...(typeof body.state === "string" && body.state.trim()
          ? { state: body.state.trim() }
          : {}),
        strategy_profile: body.strategy_profile ?? "balanced",
        dry_run: dryRun,
      }),
    });

    if (!upstream.ok) {
      const upstreamBody = await upstream.text();
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
    return NextResponse.json({
      query: {
        city: body.city.trim(),
        service: body.service.trim(),
        ...(typeof body.state === "string" && body.state.trim()
          ? { state: body.state.trim() }
          : {}),
      },
      score_result: {
        opportunity_score: data.opportunity_score,
        classification_label: data.classification_label,
      },
      report_id: data.report_id,
      status: "success",
    });
  } catch (err) {
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
