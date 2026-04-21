import Link from "next/link";
import { Icon, I } from "@/lib/icons";
import UserMenu from "./UserMenu";

type NavId = "home" | "finder" | "recs" | "reports";

const NAV: { id: NavId; label: string; d: string; href: string }[] = [
  { id: "home", label: "Home", d: I.home, href: "/" },
  { id: "finder", label: "Niche finder", d: I.search, href: "/niche-finder" },
  { id: "recs", label: "Recommendations", d: I.target, href: "/recommendations" },
  { id: "reports", label: "Reports", d: I.list, href: "/reports" },
];

const SAVED = [
  "Mid‑tier aggregator plays",
  "Roofing sweep — Mountain West",
  "Fast‑path pack opportunities",
];

export default function Sidebar({ active }: { active: NavId }) {
  const adminUrl = process.env.NEXT_PUBLIC_ADMIN_URL ?? "http://localhost:3001";

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

      <div className="sidebar-section">Saved</div>
      {SAVED.map((label) => (
        <div key={label} className="sidebar-item">
          <Icon d={I.star} />{" "}
          <span
            style={{
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {label}
          </span>
        </div>
      ))}

      <UserMenu
        name="Alex Rivera"
        plan="Pro plan"
        initials="AR"
        adminUrl={adminUrl}
      />
    </aside>
  );
}
