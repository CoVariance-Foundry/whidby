import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

const ALLOWED_STATUSES = new Set(["open", "resolved", "all"]);
const ALLOWED_SEVERITIES = new Set(["critical", "error", "warning"]);

export async function GET(req: NextRequest) {
  const supabase = await createClient();
  const statusParam = req.nextUrl.searchParams.get("status") ?? "open";
  const severityParam = req.nextUrl.searchParams.get("severity");
  const limitParam = Number(req.nextUrl.searchParams.get("limit") ?? 50);
  const status = ALLOWED_STATUSES.has(statusParam) ? statusParam : "open";
  const severity =
    severityParam && ALLOWED_SEVERITIES.has(severityParam) ? severityParam : null;
  const limit = Number.isFinite(limitParam)
    ? Math.min(Math.max(Math.trunc(limitParam), 1), 100)
    : 50;

  const { data, error } = await supabase.rpc("list_billing_operation_events", {
    p_status: status,
    p_severity: severity,
    p_limit: limit,
  });

  if (error) {
    const statusCode = error.code === "42501" ? 403 : 502;
    return NextResponse.json(
      {
        status: "unavailable",
        code: error.code === "42501" ? "billing_admin_required" : "billing_issues_unavailable",
        message:
          error.code === "42501"
            ? "Admin access is required."
            : "Billing issues could not load.",
      },
      { status: statusCode },
    );
  }

  return NextResponse.json({ status: "success", issues: data ?? [] });
}
