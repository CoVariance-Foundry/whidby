"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { isSafeNext } from "@/lib/auth/safe-next";

type Status = "idle" | "loading" | "error";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
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
    } else {
      const nextParam = searchParams.get("next");
      const dest = isSafeNext(nextParam) ? nextParam : "/reports";
      router.replace(dest);
      router.refresh();
    }
  }

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
            disabled={status === "loading"}
            className="btn-primary"
            style={{
              justifyContent: "center",
              marginTop: 4,
              opacity: status === "loading" ? 0.6 : 1,
              cursor: status === "loading" ? "not-allowed" : "pointer",
            }}
          >
            {status === "loading" ? "Signing in…" : "Sign in"}
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
