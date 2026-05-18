import Link from "next/link";
import { Icon, I } from "@/lib/icons";
import { resolveEntitlementContext } from "@/lib/account/entitlements";
import { getPlanLabel } from "@/lib/account/summary";
import { createClient } from "@/lib/supabase/server";
import UserMenu from "./UserMenu";

type NavId = "home" | "finder" | "explore" | "strategies" | "recs" | "reports" | "settings";

const NAV: { id: NavId; label: string; d: string; href: string }[] = [
  { id: "home", label: "Home", d: I.home, href: "/" },
  { id: "finder", label: "Niche finder", d: I.search, href: "/niche-finder" },
  { id: "explore", label: "Explore", d: I.map, href: "/explore" },
  { id: "strategies", label: "Strategies", d: I.sliders, href: "/strategies" },
  { id: "recs", label: "Recommendations", d: I.target, href: "/recommendations" },
  { id: "reports", label: "Reports", d: I.list, href: "/reports" },
];

function deriveInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

export default async function Sidebar({
  active,
  planLabel,
}: {
  active: NavId;
  planLabel?: string;
}) {
  const adminUrl = process.env.NEXT_PUBLIC_ADMIN_URL ?? "http://localhost:3001";

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  const fullName =
    user?.user_metadata?.full_name ??
    user?.user_metadata?.name ??
    user?.email ??
    "User";
  const email = user?.email ?? fullName;
  const initials = deriveInitials(fullName);
  let plan = planLabel ? `${planLabel} plan` : "Free plan";
  if (!planLabel) {
    try {
      const { entitlement } = await resolveEntitlementContext(supabase);
      plan = `${getPlanLabel(entitlement.plan_key)} plan`;
    } catch {
      plan = "Free plan";
    }
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-mark">W</div>
        Widby
      </div>

      {NAV.map((item) => {
        const isActive = active === item.id;
        const cls = "sidebar-item" + (isActive ? " active" : "");
        return (
          <Link
            key={item.id}
            href={item.href}
            className={cls}
            aria-current={isActive ? "page" : undefined}
          >
            <Icon d={item.d} /> {item.label}
          </Link>
        );
      })}

      <UserMenu
        name={email}
        plan={plan}
        initials={initials}
        adminUrl={adminUrl}
        accountActive={active === "settings"}
      />
    </aside>
  );
}
