"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  MessageSquare,
  ChevronLeft,
  ChevronRight,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

const NAV_ITEMS = [
  { href: "/chat", label: "Agent", icon: MessageSquare },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [signingOut, setSigningOut] = useState(false);

  async function handleSignOut() {
    setSigningOut(true);
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
  }

  return (
    <aside
      className={cn(
        "flex flex-col border-r border-[var(--color-dark-border)] bg-[var(--color-dark-alt)] transition-all duration-200",
        collapsed ? "w-16" : "w-56"
      )}
    >
      <div className="flex items-center justify-between px-4 py-5 border-b border-[var(--color-dark-border)]">
        {!collapsed && (
          <span className="text-sm font-semibold tracking-wide text-[var(--color-accent)]">
            Widby Dev
          </span>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1 rounded hover:bg-[var(--color-dark-hover)] text-[var(--color-text-muted)]"
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      <nav className="flex-1 py-3 space-y-1 px-2">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm transition-colors",
                active
                  ? "bg-[var(--color-accent-bg)] text-[var(--color-accent)]"
                  : "text-[var(--color-text-secondary)] hover:bg-[var(--color-dark-hover)] hover:text-[var(--color-text-primary)]"
              )}
            >
              <Icon size={18} />
              {!collapsed && <span>{label}</span>}
            </Link>
          );
        })}
      </nav>

      <div className="px-2 pb-4 border-t border-[var(--color-dark-border)] pt-3">
        <button
          onClick={handleSignOut}
          disabled={signingOut}
          className={cn(
            "flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-sm transition-colors",
            "text-[var(--color-text-muted)] hover:bg-[var(--color-dark-hover)] hover:text-[var(--color-negative)]",
            signingOut && "opacity-50 cursor-not-allowed"
          )}
        >
          <LogOut size={18} />
          {!collapsed && <span>{signingOut ? "Signing out..." : "Sign out"}</span>}
        </button>
      </div>
    </aside>
  );
}
