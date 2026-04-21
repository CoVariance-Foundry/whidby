import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { isSafeNext } from "@/lib/auth/safe-next";

// Forward-compatibility callback for OAuth / magic-link flows. Primary login
// uses email+password via signInWithPassword (no callback needed). Kept so
// future OAuth providers or magic-link flows degrade gracefully.
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const nextParam = searchParams.get("next");
  const next = isSafeNext(nextParam) ? nextParam : "/";
  const consumerOrigin =
    process.env.NEXT_PUBLIC_CONSUMER_APP_URL?.replace(/\/$/, "") ?? origin;

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(`${consumerOrigin}${next}`);
    }
    console.error("[auth/callback] exchangeCodeForSession failed", {
      message: error.message,
      status: error.status,
      code: error.code,
      name: error.name,
    });
    const reason = encodeURIComponent(
      error.code ?? error.message ?? "exchange_failed"
    );
    return NextResponse.redirect(
      `${origin}/login?error=auth_callback_failed&reason=${reason}`
    );
  }

  return NextResponse.redirect(
    `${origin}/login?error=auth_callback_failed&reason=no_code`
  );
}
