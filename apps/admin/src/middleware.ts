import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { isSafeNext } from "@/lib/auth/safe-next";

const PUBLIC_ROUTES = ["/login", "/auth/callback", "/api/"];

export async function middleware(request: NextRequest) {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY;
  const { pathname, search } = request.nextUrl;
  const isPublic = PUBLIC_ROUTES.some((r) => pathname.startsWith(r));

  // Let the auth callback route handle PKCE exchange without a preceding
  // middleware auth call that can mutate auth cookies.
  if (pathname.startsWith("/auth/callback")) {
    return NextResponse.next({ request });
  }

  if (!supabaseUrl || !supabaseKey) {
    console.error("[middleware] Missing Supabase env vars");
    if (!isPublic) {
      return redirectToLogin(request, null);
    }
    return NextResponse.next({ request });
  }

  let supabaseResponse = NextResponse.next({ request });

  try {
    const supabase = createServerClient(supabaseUrl, supabaseKey, {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value }) =>
              request.cookies.set(name, value)
            );
            supabaseResponse = NextResponse.next({ request });
            cookiesToSet.forEach(({ name, value, options }) =>
              supabaseResponse.cookies.set(name, value, options)
            );
          } catch (error) {
            console.warn("[middleware] Cookie setAll failed", error);
          }
        },
      },
    });

    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user && !isPublic) {
      return redirectToLogin(request, supabaseResponse, `${pathname}${search}`);
    }

    if (user && pathname === "/login") {
      const nextParam = request.nextUrl.searchParams.get("next");
      const dest = isSafeNext(nextParam) ? nextParam : "/";
      const url = request.nextUrl.clone();
      url.pathname = dest;
      url.search = "";
      return redirectWithCookies(url, supabaseResponse);
    }
  } catch (error) {
    console.error("[middleware] Auth check failed", error);
    if (!isPublic) {
      return redirectToLogin(request, supabaseResponse);
    }
  }

  return supabaseResponse;
}

// Copies cookies from a supabaseResponse (possibly holding refreshed tokens)
// onto a fresh redirect so the browser actually receives Set-Cookie headers.
function redirectWithCookies(
  url: URL,
  supabaseResponse: NextResponse | null,
): NextResponse {
  const redirect = NextResponse.redirect(url);
  if (supabaseResponse) {
    supabaseResponse.cookies.getAll().forEach((cookie) => {
      redirect.cookies.set(cookie);
    });
  }
  return redirect;
}

function redirectToLogin(
  request: NextRequest,
  supabaseResponse: NextResponse | null,
  nextPath?: string,
): NextResponse {
  const url = request.nextUrl.clone();
  url.pathname = "/login";
  url.search = "";
  if (nextPath && !PUBLIC_ROUTES.some((r) => nextPath.startsWith(r))) {
    url.searchParams.set("next", nextPath);
  }
  return redirectWithCookies(url, supabaseResponse);
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
