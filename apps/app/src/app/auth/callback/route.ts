import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

// Legacy callback for OAuth / magic-link flows. Primary login now uses
// email+password via signInWithPassword (no callback needed). Kept so
// any in-flight magic links or future OAuth providers degrade gracefully.
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const nextParam = searchParams.get("next");
  const next = nextParam?.startsWith("/") ? nextParam : "/";
  const frontendOrigin =
    process.env.NEXT_PUBLIC_APP_FRONTEND_URL?.replace(/\/$/, "") ?? origin;

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(`${frontendOrigin}${next}`);
    }
    console.error("[auth/callback] exchangeCodeForSession failed", {
      message: error.message,
      status: error.status,
      code: error.code,
      name: error.name,
    });
    const reason = encodeURIComponent(error.code ?? error.message ?? "exchange_failed");
    return NextResponse.redirect(`${frontendOrigin}/login?error=auth_callback_failed&reason=${reason}`);
  }

  return NextResponse.redirect(`${frontendOrigin}/login?error=auth_callback_failed&reason=no_code`);
}
