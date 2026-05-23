import Link from "next/link";
import { I, Icon } from "@/lib/icons";

export interface NextMoveCardProps {
  href: string;
  title: string;
  subtitle: string;
  primary?: boolean;
  ctaLabel?: string;
}

export default function NextMoveCard({
  href,
  title,
  subtitle,
  primary = false,
  ctaLabel = "Continue",
}: NextMoveCardProps) {
  return (
    <Link
      href={href}
      aria-label={`${ctaLabel}: ${title}`}
      data-primary={primary ? "true" : "false"}
      style={{
        display: "grid",
        gap: 12,
        height: "100%",
        padding: 18,
        borderRadius: 8,
        border: primary ? "1px solid var(--accent)" : "1px solid var(--rule)",
        background: primary ? "var(--accent-soft)" : "var(--paper)",
        color: "var(--ink)",
        textDecoration: "none",
        boxShadow: primary ? "0 14px 32px rgba(20, 40, 30, 0.08)" : "none",
      }}
    >
      <span style={{ display: "grid", gap: 6 }}>
        <strong style={{ fontSize: 16, lineHeight: 1.25 }}>{title}</strong>
        <span style={{ color: "var(--ink-2)", fontSize: 13.5, lineHeight: 1.45 }}>{subtitle}</span>
      </span>
      <span
        style={{
          alignItems: "center",
          color: primary ? "var(--accent-ink)" : "var(--ink)",
          display: "inline-flex",
          fontSize: 13,
          fontWeight: 700,
          gap: 8,
          justifySelf: "start",
        }}
      >
        {ctaLabel}
        <Icon d={I.arrow} size={13} />
      </span>
    </Link>
  );
}
