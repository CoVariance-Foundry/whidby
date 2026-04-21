import Link from "next/link";
import { Icon, I } from "@/lib/icons";

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

      <div className="sidebar-foot">
        <div className="sidebar-foot-av">AR</div>
        <div>
          <div style={{ color: "var(--ink)", fontWeight: 500 }}>Alex Rivera</div>
          <div style={{ color: "var(--ink-3)", fontSize: 11 }}>Pro plan</div>
        </div>
      </div>
    </aside>
  );
}
