"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";

export default function PasswordResetForm() {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const canSubmit = password.length >= 12 && password === confirm;

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!canSubmit) {
      setMessage("Use at least 12 characters and make both fields match.");
      return;
    }
    setBusy(true);
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.updateUser({ password });
      if (error) {
        setMessage(error.message);
        return;
      }
      setMessage("Password updated.");
    } catch {
      setMessage("Password could not be updated.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="settings-card" style={{ padding: 24 }} onSubmit={submit}>
      <div className="kicker">Security</div>
      <h1 className="page-h1" style={{ margin: "4px 0 8px" }}>
        Set a new password
      </h1>
      <p className="page-sub" style={{ fontStyle: "normal" }}>
        Choose a password with at least 12 characters.
      </p>
      <div style={{ display: "grid", gap: 14, marginTop: 22, maxWidth: 520 }}>
        <label style={{ display: "grid", gap: 6 }}>
          <span className="field-label">New password</span>
          <span className="input-wrap">
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 12 characters"
            />
          </span>
        </label>
        <label style={{ display: "grid", gap: 6 }}>
          <span className="field-label">Confirm password</span>
          <span className="input-wrap">
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="Re-enter your password"
            />
          </span>
        </label>
        {message && <p role="status" className="settings-muted">{message}</p>}
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <button className="btn-primary" type="submit" disabled={busy || !canSubmit}>
            Update password
          </button>
          <Link className="btn-ghost" href="/settings">
            Back to account
          </Link>
        </div>
      </div>
    </form>
  );
}
