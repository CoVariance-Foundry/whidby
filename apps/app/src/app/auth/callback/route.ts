import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

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
  }

  return NextResponse.redirect(`${frontendOrigin}/login?error=auth_callback_failed`);
}
