import { NextRequest, NextResponse } from "next/server";
import { validateNicheQueryInput } from "@/lib/niche-finder/request-validation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const validation = validateNicheQueryInput(body.queryContext ?? {});

    if (!validation.ok || !body.question?.trim()) {
      return NextResponse.json(
        {
          status: "unsupported",
          message: validation.message ?? "A follow-up question is required.",
        },
        { status: 400 }
      );
    }

    const enrichedPrompt = [
      "Exploration follow-up for niche finder.",
      `City: ${body.queryContext.city}`,
      `Service: ${body.queryContext.service}`,
      `Question: ${body.question}`,
      "Return evidence-backed answer suitable for operator review.",
    ].join("\n");

    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: enrichedPrompt }),
    });

    if (!res.ok) {
      return NextResponse.json(
        {
          responseId: crypto.randomUUID(),
          sessionId: body.sessionId,
          queryContext: body.queryContext,
          answer:
            "The exploration assistant could not complete this request right now. Try narrowing the question.",
          evidenceReferences: [],
          status: "unsupported",
        },
        { status: 502 }
      );
    }

    const data = await res.json();
    const answer = data.response ?? "No response returned.";

    return NextResponse.json({
      responseId: crypto.randomUUID(),
      sessionId: body.sessionId,
      queryContext: body.queryContext,
      answer,
      evidenceReferences: [
        { category: "demand", referenceLabel: "Demand context from query intent" },
        {
          category: "competition",
          referenceLabel: "Competition context from follow-up analysis",
        },
      ],
      status: "success",
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
