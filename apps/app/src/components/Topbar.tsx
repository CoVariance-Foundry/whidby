import { Icon, I } from "@/lib/icons";

interface Props {
  crumbs: string[];
  actions?: React.ReactNode;
}

export default function Topbar({ crumbs, actions }: Props) {
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
        {actions}
      </div>
    </div>
  );
}
