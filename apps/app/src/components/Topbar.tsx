import { Icon, I } from "@/lib/icons";

export default function Topbar({ crumbs }: { crumbs: string[] }) {
  return (
    <div className="topbar">
      <div className="crumb">
        {crumbs.map((c, i) => (
          <span key={i} style={{ display: "contents" }}>
            {i > 0 && <span>/</span>}
            {i === crumbs.length - 1 ? <b>{c}</b> : <span>{c}</span>}
          </span>
        ))}
      </div>
      <div className="topbar-actions">
        <button className="icon-btn" title="Notifications" aria-label="Notifications">
          <Icon d={I.bell} />
        </button>
        <button className="btn-ghost">
          <Icon d={I.save} /> Save search
        </button>
        <button className="btn-primary">
          <Icon d={I.plus} /> New report
        </button>
      </div>
    </div>
  );
}
