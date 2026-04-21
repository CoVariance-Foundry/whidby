"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Icon, I } from "@/lib/icons";

interface Props {
  name: string;
  plan: string;
  initials: string;
  adminUrl: string;
}

export default function UserMenu({ name, plan, initials, adminUrl }: Props) {
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const onEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onEsc);
    };
  }, [open]);

  async function handleSignOut() {
    setSigningOut(true);
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
  }

  return (
    <div ref={rootRef} style={{ position: "relative", marginTop: "auto" }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        style={{
          padding: "12px 10px 4px",
          display: "flex",
          alignItems: "center",
          gap: 10,
          fontSize: 12,
          color: "var(--ink-2)",
          borderTop: "1px solid var(--rule)",
          background: "none",
          border: "none",
          borderRadius: 0,
          width: "100%",
          textAlign: "left",
          cursor: "pointer",
        }}
      >
        <div className="sidebar-foot-av">{initials}</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ color: "var(--ink)", fontWeight: 500 }}>{name}</div>
          <div style={{ color: "var(--ink-3)", fontSize: 11 }}>{plan}</div>
        </div>
        <Icon
          d={I.sliders}
          size={12}
          style={{ color: "var(--ink-3)", flexShrink: 0 }}
        />
      </button>

      {open && (
        <div
          role="menu"
          style={{
            position: "absolute",
            bottom: "calc(100% + 6px)",
            left: 6,
            right: 6,
            background: "var(--card)",
            border: "1px solid var(--rule-strong)",
            borderRadius: 10,
            padding: 6,
            boxShadow: "0 14px 36px rgba(47,38,20,0.18)",
            zIndex: 40,
          }}
        >
          <div
            style={{
              padding: "8px 10px 10px",
              borderBottom: "1px solid var(--rule)",
              marginBottom: 4,
            }}
          >
            <div
              style={{
                fontFamily: "var(--serif)",
                fontSize: 13,
                fontWeight: 600,
                color: "var(--ink)",
                letterSpacing: "-0.1px",
              }}
            >
              {name}
            </div>
            <div
              style={{
                fontFamily: "var(--serif)",
                fontStyle: "italic",
                fontSize: 11,
                color: "var(--ink-3)",
                marginTop: 2,
              }}
            >
              {plan}
            </div>
          </div>

          <MenuLink
            label="Account settings"
            d={I.sliders}
            href="/settings"
            onClick={() => setOpen(false)}
          />
          <MenuLink
            label="Admin dashboard"
            d={I.target}
            href={adminUrl}
            external
            onClick={() => setOpen(false)}
          />

          <div
            style={{
              height: 1,
              background: "var(--rule)",
              margin: "4px 2px",
            }}
          />

          <button
            type="button"
            role="menuitem"
            onClick={handleSignOut}
            disabled={signingOut}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "7px 10px",
              width: "100%",
              borderRadius: 6,
              background: "none",
              border: "none",
              fontSize: 12.5,
              color: "var(--danger)",
              cursor: signingOut ? "not-allowed" : "pointer",
              opacity: signingOut ? 0.6 : 1,
              textAlign: "left",
              fontFamily: "inherit",
            }}
          >
            <Icon d={I.x} size={12} />
            {signingOut ? "Signing out…" : "Sign out"}
          </button>
        </div>
      )}
    </div>
  );
}

function MenuLink({
  label,
  d,
  href,
  external,
  onClick,
}: {
  label: string;
  d: string;
  href: string;
  external?: boolean;
  onClick?: () => void;
}) {
  return (
    <a
      role="menuitem"
      href={href}
      target={external ? "_blank" : undefined}
      rel={external ? "noreferrer" : undefined}
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "7px 10px",
        borderRadius: 6,
        fontSize: 12.5,
        color: "var(--ink-2)",
        textDecoration: "none",
        cursor: "pointer",
      }}
      className="user-menu-item"
    >
      <Icon d={d} size={12} style={{ color: "var(--ink-3)" }} />
      <span style={{ flex: 1 }}>{label}</span>
      {external && (
        <Icon d={I.arrow} size={10} style={{ color: "var(--ink-3)" }} />
      )}
    </a>
  );
}
