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
      const dest = isSafeNext(nextParam) ? nextParam : "/reports";
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
    <div
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        background: "var(--paper)",
        padding: 24,
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 380,
          background: "var(--card)",
          border: "1px solid var(--rule)",
          borderRadius: 12,
          padding: 28,
          boxShadow: "0 1px 0 rgba(47,38,20,0.03)",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: 20 }}>
          <div
            style={{
              display: "inline-grid",
              placeItems: "center",
              width: 36,
              height: 36,
              borderRadius: "50%",
              background: "var(--ink)",
              color: "var(--paper)",
              fontFamily: "var(--serif)",
              fontStyle: "italic",
              fontWeight: 700,
              fontSize: 18,
              marginBottom: 12,
            }}
          >
            W
          </div>
          <h1
            style={{
              fontFamily: "var(--serif)",
              fontSize: 22,
              fontWeight: 600,
              letterSpacing: "-0.3px",
              color: "var(--ink)",
            }}
          >
            Widby
          </h1>
          <p
            style={{
              marginTop: 4,
              fontFamily: "var(--serif)",
              fontStyle: "italic",
              fontSize: 13,
              color: "var(--ink-3)",
            }}
          >
            Sign in to continue
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          style={{ display: "flex", flexDirection: "column", gap: 14 }}
        >
          <div>
            <div className="field-label">Email</div>
            <div className="input-wrap">
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
            </div>
          </div>

          <div>
            <div className="field-label">Password</div>
            <div className="input-wrap">
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>
          </div>

          {status === "error" && (
            <p
              style={{
                fontSize: 12,
                color: "var(--danger)",
                fontFamily: "var(--serif)",
                fontStyle: "italic",
              }}
            >
              {errorMsg}
            </p>
          )}

          <button
            type="submit"
            disabled={isBusy}
            className="btn-primary"
            aria-live="polite"
            style={{
              justifyContent: "center",
              marginTop: 4,
              opacity: isBusy ? 0.6 : 1,
              cursor: isBusy ? "not-allowed" : "pointer",
            }}
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
