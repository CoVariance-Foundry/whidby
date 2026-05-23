import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function POST(_req: NextRequest, { params }: RouteContext) {
  const { id } = await params;
  if (!id) {
    return NextResponse.json(
      { status: "validation_error", message: "Issue id is required." },
      { status: 400 },
    );
  }

  const supabase = await createClient();
  const { error } = await supabase.rpc("resolve_billing_operation_event", {
    p_event_id: id,
  });

  if (error) {
    const statusCode = error.code === "42501" ? 403 : error.code === "P0002" ? 404 : 502;
    const code =
      error.code === "42501"
        ? "billing_admin_required"
        : error.code === "P0002"
          ? "billing_issue_not_found"
          : "billing_issue_resolve_failed";
    const message =
      error.code === "42501"
        ? "Admin access is required."
        : error.code === "P0002"
          ? "Billing issue was not found."
          : "Billing issue could not be resolved.";
    return NextResponse.json(
      {
        status: "unavailable",
        code,
        message,
      },
      { status: statusCode },
    );
  }

  return NextResponse.json({ status: "success" });
}
