import Link from "next/link";
import { Icon, I } from "@/lib/icons";

interface NextMoveCardProps {
  href: string;
  title: string;
  subtitle: string;
  primary?: boolean;
}

export default function NextMoveCard({ href, title, subtitle, primary = false }: NextMoveCardProps) {
  return (
    <Link
      href={href}
      style={{
        display: "block",
        background: "var(--card)",
        border: `1px solid ${primary ? "var(--ink)" : "var(--rule)"}`,
        borderRadius: 8,
        padding: 16,
        color: "inherit",
        textDecoration: "none",
        transition: "border-color 0.15s ease",
      }}
    >
      <div style={{ color: "var(--ink)", fontSize: 14, fontWeight: 800 }}>{title}</div>
      <div style={{ color: "var(--ink-3)", fontSize: 12, lineHeight: 1.45, marginTop: 4 }}>
        {subtitle}
      </div>
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          color: "var(--accent-ink)",
          fontSize: 12,
          fontWeight: 800,
          marginTop: 14,
        }}
      >
        Continue <Icon d={I.arrow} size={13} />
      </div>
    </Link>
  );
}
