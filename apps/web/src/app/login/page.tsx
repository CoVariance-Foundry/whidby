import { permanentRedirect } from "next/navigation";
import { isSafeNext } from "@/lib/auth/safe-next";

type SearchParams =
  | Promise<Record<string, string | string[] | undefined>>
  | Record<string, string | string[] | undefined>;

function firstParam(
  params: Record<string, string | string[] | undefined>,
  key: string,
): string | null {
  const value = params[key];
  if (Array.isArray(value)) return value[0] ?? null;
  return value ?? null;
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams?: SearchParams;
}) {
  const resolvedSearchParams = searchParams ? await searchParams : {};
  const nextParam = firstParam(resolvedSearchParams, "next");
  const next = isSafeNext(nextParam) ? nextParam : null;
  const consumerOrigin =
    process.env.NEXT_PUBLIC_CONSUMER_APP_URL?.replace(/\/$/, "") ??
    (process.env.NODE_ENV === "development" ? "http://localhost:3002" : "");

  if (!consumerOrigin) {
    console.error(
      "[apps/web/login] NEXT_PUBLIC_CONSUMER_APP_URL is unset; redirecting to home",
    );
    permanentRedirect("/");
  }

  const loginUrl = new URL("/login", consumerOrigin);
  if (next) {
    loginUrl.searchParams.set("next", next);
  }

  permanentRedirect(loginUrl.toString());
}
