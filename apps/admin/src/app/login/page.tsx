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
    }, 250);
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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (isBusy) return;
    setStatus("loading");
    setErrorMsg("");

    const supabase = createClient();
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) {
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
      ? "Signing in..."
      : isLocked
        ? `Try again in ${remainingSec}s`
        : "Sign in";

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--color-dark)]">
      <div className="w-full max-w-sm space-y-6 rounded-xl border border-[var(--color-dark-border)] bg-[var(--color-dark-card)] p-8">
        <div className="space-y-2 text-center">
          <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">
            Widby Dev Suite
          </h1>
          <p className="text-sm text-[var(--color-text-muted)]">
            Sign in to your account
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="email"
              className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5"
            >
              Email address
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full rounded-lg border border-[var(--color-dark-border)] bg-[var(--color-dark)] px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-accent)] focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              className="w-full rounded-lg border border-[var(--color-dark-border)] bg-[var(--color-dark)] px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-accent)] focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
            />
          </div>

          {status === "error" && (
            <p className="text-xs text-[var(--color-negative)]">{errorMsg}</p>
          )}

          <button
            type="submit"
            disabled={isBusy}
            aria-live="polite"
            className="w-full rounded-lg bg-[var(--color-accent)] px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--color-accent-dark)] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {buttonLabel}
          </button>
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
