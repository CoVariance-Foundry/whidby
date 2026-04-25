import { NextRequest, NextResponse } from "next/server";
import { searchMetros } from "@/lib/niche-finder/cbsa-search";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const q = searchParams.get("q") ?? "";
  const limit = Math.min(Math.max(Number(searchParams.get("limit") ?? "10"), 1), 20);

  const results = searchMetros(q, limit);
  return NextResponse.json(results);
}
