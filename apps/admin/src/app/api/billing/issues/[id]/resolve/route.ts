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
    const statusCode = error.code === "42501" ? 403 : 502;
    return NextResponse.json(
      {
        status: "unavailable",
        code: error.code === "42501" ? "billing_admin_required" : "billing_issue_resolve_failed",
        message:
          error.code === "42501"
            ? "Admin access is required."
            : "Billing issue could not be resolved.",
      },
      { status: statusCode },
    );
  }

  return NextResponse.json({ status: "success" });
}
