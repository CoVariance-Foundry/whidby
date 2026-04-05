import { NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${API_BASE}/api/graph`);
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { nodes: [], edges: [], summary: { total_nodes: 0, total_edges: 0, node_type_counts: {} } },
      { status: 502 }
    );
  }
}
