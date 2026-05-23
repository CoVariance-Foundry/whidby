"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Icon, I } from "@/lib/icons";
import { createClient } from "@/lib/supabase/client";

export interface NavbarUser {
  email: string;
  displayName: string;
  initials: string;
  planLabel: string;
  scansUsed: number;
  scansLimit: number;
  adminUrl: string;
  isAdmin: boolean;
  freshReportQuotaExempt: boolean;
}

const NAV_ITEMS = [
  { href: "/", label: "Home", match: (path: string) => path === "/" },
  {
    href: "/strategies",
    label: "Strategies",
    match: (path: string) => path.startsWith("/strategies"),
  },
  { href: "/explore", label: "Explore", match: (path: string) => path === "/explore" },
  {
    href: "/agency",
    label: "Multi-market",
    match: (path: string) => path.startsWith("/agency"),
  },
  {
    href: "/reports",
    label: "Reports",
    match: (path: string) => path.startsWith("/reports") || path.startsWith("/report/"),
  },
] as const;

export default function Navbar({ user }: { user: NavbarUser }) {
  const pathname = usePathname() ?? "/";
  const [mobileOpen, setMobileOpen] = useState(false);
  const inOnboarding =
    pathname.startsWith("/signup") || pathname.startsWith("/onboarding");

  return (
    <nav className="navbar" aria-label="Primary navigation">
      <div className="navbar-inner">
        <Link href="/" className="navbar-brand" aria-label="Widby home">
          <span className="navbar-mark" aria-hidden="true">
            W
          </span>
          <span>Widby</span>
        </Link>

        {inOnboarding ? (
          <div className="navbar-links" aria-label="Onboarding navigation">
            <Link href="/" className="navbar-link">
              Back to home
            </Link>
          </div>
        ) : (
          <div className="navbar-links" aria-label="Authenticated product navigation">
            {NAV_ITEMS.map((item) => {
              const active = item.match(pathname);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`navbar-link${active ? " active" : ""}`}
                  aria-current={active ? "page" : undefined}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        )}

        <div className="navbar-actions">
          <UsagePill user={user} />
          <ProfileMenu user={user} />
          <button
            type="button"
            className="navbar-mobile-toggle"
            aria-expanded={mobileOpen}
            aria-controls="navbar-mobile-menu"
            aria-label="Toggle navigation menu"
            onClick={() => setMobileOpen((open) => !open)}
          >
            <span />
            <span />
            <span />
          </button>
        </div>
      </div>

      {mobileOpen && !inOnboarding && (
        <div id="navbar-mobile-menu" className="navbar-mobile-menu">
          {NAV_ITEMS.map((item) => {
            const active = item.match(pathname);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`navbar-mobile-link${active ? " active" : ""}`}
                aria-current={active ? "page" : undefined}
                onClick={() => setMobileOpen(false)}
              >
                {item.label}
              </Link>
            );
          })}
          <Link
            href="/settings"
            className="navbar-mobile-link"
            onClick={() => setMobileOpen(false)}
          >
            Account settings
          </Link>
        </div>
      )}
    </nav>
  );
}

function UsagePill({ user }: { user: NavbarUser }) {
  const scansLimit = Math.max(0, user.scansLimit);
  const scansUsed = Math.max(0, user.scansUsed);
  const usageLabel = user.freshReportQuotaExempt
    ? "Unlimited scans"
    : `${scansUsed}/${scansLimit} scans`;

  return (
    <div className="navbar-usage" aria-label="Plan usage">
      {/* Assumption for WHI-46: scans map to the existing fresh-report quota model. */}
      <span className="navbar-usage-count">{usageLabel}</span>
      <span className="navbar-usage-separator" aria-hidden="true">
        /
      </span>
      <span className="navbar-usage-plan">{user.planLabel}</span>
    </div>
  );
}

function ProfileMenu({ user }: { user: NavbarUser }) {
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (!open) return;
    const onDown = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onEsc = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
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
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
      router.push("/login");
    } catch {
      // Keep the menu usable so a transient auth/network failure can be retried.
    } finally {
      setSigningOut(false);
    }
  }

  return (
    <div ref={rootRef} className="navbar-profile">
      <button
        type="button"
        className="navbar-profile-button"
        onClick={() => setOpen((value) => !value)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Open account menu for ${user.email}`}
      >
        <span className="navbar-avatar" aria-hidden="true">
          {user.initials}
        </span>
        <span className="navbar-profile-copy">
          <span>{user.displayName}</span>
          <small>{user.planLabel} plan</small>
        </span>
        <Icon d={I.chevronDown} size={12} />
      </button>

      {open && (
        <div className="navbar-profile-menu" role="menu">
          <div className="navbar-profile-meta">
            <strong>{user.email}</strong>
            <span>{user.planLabel} plan</span>
          </div>
          <MenuLink href="/settings" label="Account settings" onClick={() => setOpen(false)} />
          <MenuLink href="/settings/password" label="Password" onClick={() => setOpen(false)} />
          {user.isAdmin && (
            <MenuLink
              href={user.adminUrl}
              label="Admin dashboard"
              external
              onClick={() => setOpen(false)}
            />
          )}
          <button
            type="button"
            role="menuitem"
            className="navbar-profile-danger"
            disabled={signingOut}
            onClick={handleSignOut}
          >
            <Icon d={I.x} size={12} />
            {signingOut ? "Signing out..." : "Sign out"}
          </button>
        </div>
      )}
    </div>
  );
}

function MenuLink({
  href,
  label,
  external,
  onClick,
}: {
  href: string;
  label: string;
  external?: boolean;
  onClick?: () => void;
}) {
  if (!external) {
    return (
      <Link href={href} role="menuitem" className="navbar-profile-link" onClick={onClick}>
        {label}
      </Link>
    );
  }

  return (
    <a
      href={href}
      role="menuitem"
      target="_blank"
      rel="noreferrer"
      className="navbar-profile-link"
      onClick={onClick}
    >
      {label}
    </a>
  );
}
