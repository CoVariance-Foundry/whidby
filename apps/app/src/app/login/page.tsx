"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

type Status = "idle" | "loading" | "sent" | "error";

export default function LoginPage() {
  const [email, setEmail] = useState("antwoine@covariance.studio");
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("loading");
    setErrorMsg("");

    const supabase = createClient();
    const frontendOrigin =
      process.env.NEXT_PUBLIC_APP_FRONTEND_URL?.replace(/\/$/, "") ??
      window.location.origin;
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${frontendOrigin}/auth/callback?next=/`,
      },
    });

    if (error) {
      setErrorMsg(error.message);
      setStatus("error");
    } else {
      setStatus("sent");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--color-dark)]">
      <div className="w-full max-w-sm space-y-6 rounded-xl border border-[var(--color-dark-border)] bg-[var(--color-dark-card)] p-8">
        <div className="space-y-2 text-center">
          <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">
            Widby Dev Suite
          </h1>
          <p className="text-sm text-[var(--color-text-muted)]">
            Sign in with a magic link
          </p>
        </div>

        {status === "sent" ? (
          <div className="rounded-lg border border-[var(--color-accent)]/30 bg-[var(--color-accent-bg)] p-4 text-center">
            <p className="text-sm text-[var(--color-accent-light)]">
              Check your email for a sign-in link.
            </p>
            <button
              onClick={() => setStatus("idle")}
              className="mt-3 text-xs text-[var(--color-text-muted)] underline hover:text-[var(--color-text-secondary)]"
            >
              Try a different email
            </button>
          </div>
        ) : (
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

            {status === "error" && (
              <p className="text-xs text-[var(--color-negative)]">{errorMsg}</p>
            )}

            <button
              type="submit"
              disabled={status === "loading"}
              className="w-full rounded-lg bg-[var(--color-accent)] px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--color-accent-dark)] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {status === "loading" ? "Sending..." : "Send magic link"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
