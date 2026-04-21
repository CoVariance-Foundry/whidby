import { NextRequest, NextResponse } from "next/server";
import { validateNicheQueryInput } from "@/lib/niche-finder/request-validation";
import { buildExplorationResponse } from "@/lib/niche-finder/response-adapter";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const validation = validateNicheQueryInput(body);

    if (!validation.ok) {
      return NextResponse.json(
        {
          status: "validation_error",
          message: validation.message,
        },
        { status: 400 }
      );
    }

    return NextResponse.json(
      buildExplorationResponse({
        city: body.city.trim(),
        service: body.service.trim(),
      })
    );
  } catch {
    return NextResponse.json(
      {
        status: "unavailable",
        message: "Failed to process exploration request.",
      },
      { status: 502 }
    );
  }
}
