"use client";

import Link from "next/link";
import { ARCHETYPES } from "@/lib/archetypes";
import type { ExploreCachedScore } from "@/lib/explore/types";
import { ScoreCircle } from "@/components/ScoreVisuals";
import { formatDate, formatDecimal, formatPercent, humanize } from "./format";

interface ServiceScoreRowProps {
  score: ExploreCachedScore;
  selected: boolean;
  onToggle: () => void;
}

function archetypeClass(id: ExploreCachedScore["archetype_id"]): string {
  return ARCHETYPES.find((a) => a.id === id)?.glyph ?? "arch-mixed";
}

export default function ServiceScoreRow({
  score,
  selected,
  onToggle,
}: ServiceScoreRowProps) {
  const checkboxId = `select-service-${score.report_id}`;

  return (
    <div
      role="listitem"
      style={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr) auto",
        gap: 12,
        alignItems: "center",
        padding: "12px 0",
        borderBottom: "1px solid var(--rule)",
      }}
    >
      <Link
        href={`/reports?open=${encodeURIComponent(score.report_id)}`}
        aria-label={`Open cached report for ${score.service}`}
        style={{
          minWidth: 0,
          display: "grid",
          gap: 7,
          color: "inherit",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            minWidth: 0,
            flexWrap: "wrap",
          }}
        >
          <span
            style={{
              fontFamily: "var(--sans)",
              fontSize: 14,
              fontWeight: 650,
              color: "var(--ink)",
            }}
          >
            {score.service}
          </span>
          <span
            className={archetypeClass(score.archetype_id)}
            style={{
              display: "inline-block",
              padding: "2px 9px",
              borderRadius: 999,
              fontFamily: "var(--sans)",
              fontSize: 11,
              fontWeight: 650,
              textTransform: "uppercase",
              letterSpacing: "0.02em",
            }}
          >
            {score.archetype_label}
          </span>
        </div>
        <div
          style={{
            display: "flex",
            gap: 10,
            flexWrap: "wrap",
            fontFamily: "var(--sans)",
            fontSize: 12,
            color: "var(--ink-3)",
          }}
        >
          <span>Scored {formatDate(score.last_scored_at)}</span>
          {score.score_system && <span>{score.score_system.toUpperCase()}</span>}
          {score.confidence_score != null && <span>Confidence {Math.round(score.confidence_score)}</span>}
          {score.ai_resilience_score != null && <span>AI resilience {Math.round(score.ai_resilience_score)}</span>}
          {score.ai_exposure && <span>AI {humanize(score.ai_exposure)}</span>}
          {score.difficulty_tier && <span>{humanize(score.difficulty_tier)}</span>}
          {score.business_density_per_1k != null && (
            <span>Density {formatDecimal(score.business_density_per_1k)}</span>
          )}
          {score.growth_available && score.establishment_growth_yoy != null && (
            <span>Growth {formatPercent(score.establishment_growth_yoy)}</span>
          )}
        </div>
      </Link>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "auto auto",
          gap: 10,
          alignItems: "center",
        }}
      >
        <ScoreCircle value={score.opportunity_score} label={`${score.service} opportunity score`} size={46} />
        <label
          htmlFor={checkboxId}
          style={{
            width: 34,
            height: 34,
            border: "1px solid var(--rule-strong)",
            borderRadius: 8,
            display: "grid",
            placeItems: "center",
            background: selected ? "var(--accent-soft)" : "var(--card)",
            color: selected ? "var(--accent-ink)" : "var(--ink-3)",
            cursor: "pointer",
          }}
        >
          <input
            id={checkboxId}
            type="checkbox"
            aria-label={`Select ${score.service} for fresh scan`}
            checked={selected}
            onChange={onToggle}
            style={{ width: 16, height: 16, accentColor: "var(--accent)" }}
          />
        </label>
      </div>
    </div>
  );
}
