import Link from "next/link";
import { Icon, I } from "@/lib/icons";
import { createClient } from "@/lib/supabase/server";
import UserMenu from "./UserMenu";

type NavId = "home" | "finder" | "recs" | "reports";

const NAV: { id: NavId; label: string; d: string; href: string }[] = [
  { id: "home", label: "Home", d: I.home, href: "/" },
  { id: "finder", label: "Niche finder", d: I.search, href: "/niche-finder" },
  { id: "recs", label: "Recommendations", d: I.target, href: "/recommendations" },
  { id: "reports", label: "Reports", d: I.list, href: "/reports" },
];

function deriveInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

export default async function Sidebar({ active }: { active: NavId }) {
  const adminUrl = process.env.NEXT_PUBLIC_ADMIN_URL ?? "http://localhost:3001";

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  const fullName =
    user?.user_metadata?.full_name ??
    user?.user_metadata?.name ??
    user?.email ??
    "User";
  const initials = deriveInitials(fullName);

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-mark">W</div>
        Widby
      </div>

      {NAV.map((item) => {
        const cls = "sidebar-item" + (active === item.id ? " active" : "");
        return (
          <Link key={item.id} href={item.href} className={cls}>
            <Icon d={item.d} /> {item.label}
          </Link>
        );
      })}

      <UserMenu
        name={fullName}
        plan="Pro plan"
        initials={initials}
        adminUrl={adminUrl}
      />
    </aside>
  );
}
