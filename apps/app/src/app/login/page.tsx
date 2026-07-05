"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { isSafeNext } from "@/lib/auth/safe-next";

type Status = "idle" | "loading" | "error";

// Progressive backoff caps UI-driven credential stuffing attempts. After each
// failure: 1s, 2s, 4s, 8s, 15s (capped). Resets on success or page refresh.
// TODO: Replace with server-side IP-based rate-limiting (e.g. @upstash/ratelimit
// in middleware or a /api/auth/login route handler) once Redis is provisioned.
const MAX_LOCK_MS = 15_000;
const LOGIN_TIMEOUT_MS = 12_000;
function computeLockMs(failCount: number): number {
  if (failCount <= 0) return 0;
  return Math.min(1000 * 2 ** (failCount - 1), MAX_LOCK_MS);
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [lockedUntil, setLockedUntil] = useState<number | null>(null);
  const [now, setNow] = useState<number>(() => Date.now());
  const failCountRef = useRef(0);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Drive the countdown UI while a lock is active; tear down on unmount.
  // Tick once per visible second — display uses Math.ceil(remainingMs/1000),
  // so sub-second ticks would just burn renders and repeat identical AT text.
  useEffect(() => {
    if (lockedUntil === null) return;
    tickRef.current = setInterval(() => {
      const current = Date.now();
      setNow(current);
      if (current >= lockedUntil) {
        setLockedUntil(null);
        if (tickRef.current) {
          clearInterval(tickRef.current);
          tickRef.current = null;
        }
      }
    }, 1000);
    return () => {
      if (tickRef.current) {
        clearInterval(tickRef.current);
        tickRef.current = null;
      }
    };
  }, [lockedUntil]);

  const remainingMs =
    lockedUntil !== null ? Math.max(0, lockedUntil - now) : 0;
  const isLocked = remainingMs > 0;
  const remainingSec = Math.ceil(remainingMs / 1000);
  const isBusy = status === "loading" || isLocked;

  async function signInWithTimeout(email: string, password: string) {
    const supabase = createClient();
    let timeoutHandle: ReturnType<typeof setTimeout> | null = null;
    const timeoutPromise = new Promise<{ error: { message: string } }>(
      (resolve) => {
        timeoutHandle = setTimeout(() => {
          resolve({
            error: {
              message:
                "Sign-in timed out. Check API health and try again in a few seconds.",
            },
          });
        }, LOGIN_TIMEOUT_MS);
      },
    );

    const signInPromise = supabase.auth.signInWithPassword({ email, password });
    const result = await Promise.race([signInPromise, timeoutPromise]);
    if (timeoutHandle) {
      clearTimeout(timeoutHandle);
    }
    return result;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (isBusy) return;
    setStatus("loading");
    setErrorMsg("");

    const { error } = await signInWithTimeout(email, password);

    if (error) {
      console.error("[login] sign-in failed", {
        message: error.message,
        email_domain: email.includes("@") ? email.split("@")[1] : "unknown",
      });
      setErrorMsg(error.message);
      setStatus("error");
      failCountRef.current += 1;
      const lockMs = computeLockMs(failCountRef.current);
      if (lockMs > 0) {
        setLockedUntil(Date.now() + lockMs);
        setNow(Date.now());
      }
    } else {
      failCountRef.current = 0;
      setLockedUntil(null);
      const nextParam = searchParams.get("next");
      const dest = isSafeNext(nextParam) ? nextParam : "/";
      router.replace(dest);
      router.refresh();
    }
  }

  const buttonLabel =
    status === "loading"
      ? "Signing in…"
      : isLocked
        ? `Try again in ${remainingSec}s`
        : "Sign in";

  return (
    <div className="grid min-h-screen place-items-center bg-white px-6 py-10">
      <div className="w-full max-w-sm rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
        <div className="mb-6 space-y-2 text-center">
          <div className="mb-2 inline-flex items-center gap-2">
            <div className="grid h-8 w-8 place-items-center rounded-lg bg-[#141414]">
              <svg
                aria-hidden="true"
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
              >
                <circle cx="8" cy="8" r="6" stroke="#10B981" strokeWidth="2" />
                <circle cx="8" cy="8" r="2.5" fill="#10B981" />
              </svg>
            </div>
            <h1 className="text-lg font-bold tracking-normal text-[#141414]">
              Widby
            </h1>
          </div>
          <h2 className="text-xl font-semibold tracking-normal text-gray-900">
            Welcome back
          </h2>
          <p className="text-sm text-gray-500">Sign in to your account</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="email"
              className="mb-1.5 block text-xs font-medium text-gray-600"
            >
              Email address
            </label>
            <input
              id="email"
              autoComplete="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-[#10B981] focus:outline-none focus:ring-1 focus:ring-[#10B981]"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="mb-1.5 block text-xs font-medium text-gray-600"
            >
              Password
            </label>
            <input
              id="password"
              autoComplete="current-password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-[#10B981] focus:outline-none focus:ring-1 focus:ring-[#10B981]"
            />
          </div>

          {status === "error" && (
            <p className="text-xs text-red-600" role="alert">
              {errorMsg}
            </p>
          )}

          <button
            type="submit"
            disabled={isBusy}
            className="w-full rounded-lg bg-[#141414] px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {buttonLabel}
          </button>

          {isLocked && (
            <p
              role="status"
              aria-live="polite"
              className="text-center text-xs text-gray-500"
            >
              Try again in {remainingSec}s
            </p>
          )}
        </form>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
