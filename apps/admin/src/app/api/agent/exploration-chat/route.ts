import { NextRequest, NextResponse } from "next/server";
import { validateNicheQueryInput } from "@/lib/niche-finder/request-validation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const ctx = body.query_context ?? {};
    const validation = validateNicheQueryInput(ctx);

    if (!validation.ok || !body.question?.trim()) {
      return NextResponse.json(
        {
          status: "unsupported",
          message: validation.message ?? "A follow-up question is required.",
        },
        { status: 400 }
      );
    }

    const res = await fetch(`${API_BASE}/api/exploration/followup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        city: ctx.city.trim(),
        service: ctx.service.trim(),
        question: body.question.trim(),
      }),
    });

    if (!res.ok) {
      return NextResponse.json(
        {
          response_id: crypto.randomUUID(),
          session_id: body.session_id ?? "",
          query_context: ctx,
          answer:
            "The exploration assistant could not complete this request. Try narrowing the question.",
          evidence_references: [],
          status: "unsupported",
        },
        { status: 502 }
      );
    }

    const data = await res.json();

    return NextResponse.json({
      response_id: crypto.randomUUID(),
      session_id: body.session_id ?? "",
      query_context: ctx,
      answer: data.answer ?? "No response returned.",
      evidence_references: data.evidence_references ?? [],
      status: data.status ?? "success",
    });
  } catch {
    return NextResponse.json(
      {
        status: "unsupported",
        message: "Failed to process exploration assistant request.",
      },
      { status: 502 }
    );
  }
}
