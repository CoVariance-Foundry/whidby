"use client";

import { useState } from "react";
import type { ExploreCachedScore, ExploreCitySummary } from "@/lib/explore/types";
import { Icon, I } from "@/lib/icons";
import { scoreToneForValue } from "@/lib/design-tokens";
import {
  formatCurrency,
  formatDecimal,
  formatInteger,
  formatPercent,
  humanize,
} from "./format";

export type ExploreSortKey =
  | "city"
  | "population"
  | "income"
  | "business_density"
  | "growth"
  | "cached_services"
  | "best_opportunity";

export type SortDirection = "asc" | "desc";

interface ExploreTableProps {
  cities: ExploreCitySummary[];
  sortKey: ExploreSortKey;
  sortDirection: SortDirection;
  activeService?: string;
  detailStates?: Record<string, ExploreCityDetailState>;
  onCityExpand: (city: ExploreCitySummary) => void;
  onSortChange: (key: ExploreSortKey) => void;
  onCityOpen: (city: ExploreCitySummary) => void;
  onReset: () => void;
}

export type ExploreCityDetailState =
  | { status: "loading" }
  | { status: "error"; message: string };

const COLUMNS: Array<{ key: ExploreSortKey; label: string; align?: "right" }> = [
  { key: "city", label: "City" },
  { key: "population", label: "Pop.", align: "right" },
  { key: "income", label: "Median HH income", align: "right" },
  { key: "business_density", label: "Biz density", align: "right" },
  { key: "growth", label: "Growth YoY", align: "right" },
  { key: "best_opportunity", label: "Best score", align: "right" },
  { key: "cached_services", label: "Services", align: "right" },
];

function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "-";
  const diff = Date.now() - then;
  const days = Math.floor(diff / 86_400_000);
  if (days < 1) return "today";
  if (days === 1) return "1 day ago";
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  if (months === 1) return "1 month ago";
  return `${months} months ago`;
}

function displayScore(score: number | null | undefined): string {
  return score != null ? String(score) : "-";
}

function SortIcon({ active, direction }: { active: boolean; direction: SortDirection }) {
  if (!active) return <Icon d={I.chevronDown} size={12} style={{ opacity: 0.35 }} />;
  return <Icon d={direction === "asc" ? I.arrowUp : I.arrowDown} size={12} />;
}

function HeaderCell({
  column,
  sortKey,
  sortDirection,
  onSortChange,
}: {
  column: (typeof COLUMNS)[number];
  sortKey: ExploreSortKey;
  sortDirection: SortDirection;
  onSortChange: (key: ExploreSortKey) => void;
}) {
  const active = sortKey === column.key;
  return (
    <span
      role="columnheader"
      aria-sort={active ? (sortDirection === "asc" ? "ascending" : "descending") : "none"}
      style={{ textAlign: column.align, minWidth: 0 }}
    >
      <button
        type="button"
        aria-label={`Sort by ${column.label}`}
        onClick={() => onSortChange(column.key)}
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: column.align === "right" ? "flex-end" : "flex-start",
          gap: 5,
          width: "100%",
          minHeight: 24,
          color: active ? "var(--ink)" : "var(--ink-3)",
          fontFamily: "var(--sans)",
          fontSize: 11.5,
          fontWeight: 650,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
        }}
      >
        {column.label}
        <SortIcon active={active} direction={sortDirection} />
      </button>
    </span>
  );
}

function ServiceDetailRow({
  score,
  isHighlighted,
}: {
  score: ExploreCachedScore;
  isHighlighted: boolean;
}) {
  return (
    <div
      role="row"
      style={{
        display: "grid",
        gridTemplateColumns: "minmax(160px, 1.4fr) repeat(4, minmax(80px, 1fr))",
        gap: 12,
        alignItems: "center",
        padding: "8px 16px 8px 48px",
        borderBottom: "1px solid var(--rule)",
        fontFamily: "var(--sans)",
        fontSize: 12.5,
        color: "var(--ink-2)",
        background: isHighlighted ? "var(--accent-soft)" : "transparent",
        borderLeft: isHighlighted ? "3px solid var(--accent)" : "3px solid transparent",
      }}
    >
      <span role="cell" style={{ fontWeight: isHighlighted ? 700 : 500 }}>
        {humanize(score.service || score.niche_normalized || "")}
      </span>
      <span
        role="cell"
        style={{
          textAlign: "right",
          fontFamily: "var(--mono)",
          fontWeight: 700,
          color: scoreToneForValue(score.opportunity_score).text,
        }}
      >
        {displayScore(score.opportunity_score)}
      </span>
      <span role="cell" style={{ textAlign: "right" }}>
        {score.archetype_label || "-"}
      </span>
      <span role="cell" style={{ textAlign: "right" }}>
        {score.difficulty_tier ? humanize(score.difficulty_tier) : "-"}
      </span>
      <span
        role="cell"
        style={{
          textAlign: "right",
          fontFamily: "var(--sans)",
          fontSize: 11.5,
          color: "var(--ink-3)",
        }}
      >
        {relativeTime(score.last_scored_at || score.latest_scored_at)}
      </span>
    </div>
  );
}

function CityRow({
  city,
  isExpanded,
  activeService,
  detailState,
  onToggle,
  onCityOpen,
}: {
  city: ExploreCitySummary;
  isExpanded: boolean;
  activeService: string;
  detailState?: ExploreCityDetailState;
  onToggle: () => void;
  onCityOpen: () => void;
}) {
  const normalizedActiveService = activeService
    .trim()
    .toLocaleLowerCase()
    .replace(/[_-]+/g, " ");
  const needsFullServiceDetail = city.cached_services_count > city.cached_scores.length;

  return (
    <>
      <div
        role="row"
        aria-label={`Open ${city.cbsa_name}`}
        tabIndex={0}
        onClick={onCityOpen}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onCityOpen();
          }
        }}
        style={{
          display: "grid",
          gridTemplateColumns:
            "minmax(220px, 1.8fr) repeat(5, minmax(92px, 0.8fr)) minmax(72px, 0.6fr) 32px",
          gap: 12,
          alignItems: "center",
          padding: "13px 16px",
          borderBottom: isExpanded ? "none" : "1px solid var(--rule)",
          fontFamily: "var(--sans)",
          fontSize: 13.5,
          color: "var(--ink)",
          background: isExpanded ? "var(--paper-alt)" : "transparent",
          cursor: "pointer",
        }}
      >
        <span
          role="cell"
          style={{ minWidth: 0 }}
        >
          <span
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              minWidth: 0,
            }}
          >
            <span
              style={{
                minWidth: 0,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                fontWeight: 650,
              }}
            >
              {city.cbsa_name}
            </span>
            {city.cached_scores.some((s) => s.is_stale) && (
              <span
                style={{
                  flex: "0 0 auto",
                  padding: "2px 7px",
                  borderRadius: 999,
                  background: "var(--accent-soft)",
                  color: "var(--accent-ink)",
                  fontSize: 11,
                  fontWeight: 700,
                }}
              >
                Stale
              </span>
            )}
          </span>
          <span
            style={{
              display: "block",
              marginTop: 2,
              fontFamily: "var(--serif)",
              fontStyle: "italic",
              fontSize: 12,
              color: "var(--ink-3)",
            }}
          >
            {city.state}
          </span>
        </span>

        <span role="cell" style={{ textAlign: "right", fontFamily: "var(--mono)" }}>
          {formatInteger(city.population)}
        </span>
        <span role="cell" style={{ textAlign: "right", fontFamily: "var(--mono)" }}>
          {formatCurrency(city.median_household_income_usd)}
        </span>
        <span role="cell" style={{ textAlign: "right", fontFamily: "var(--mono)" }}>
          {formatDecimal(city.business_density_per_1k)}
        </span>
        <span role="cell" style={{ textAlign: "right", fontFamily: "var(--mono)" }}>
          {formatPercent(city.establishment_growth_yoy)}
        </span>
        <span
          role="cell"
          style={{
            textAlign: "right",
            fontFamily: "var(--mono)",
            color: scoreToneForValue(city.best_opportunity_score).text,
            fontWeight: 700,
          }}
        >
          {displayScore(city.best_opportunity_score)}
        </span>
        <span
          role="cell"
          style={{
            textAlign: "right",
            fontFamily: "var(--mono)",
            fontSize: 12,
          }}
        >
          {city.cached_services_count}
        </span>
        <span role="cell" style={{ textAlign: "center" }}>
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              onToggle();
            }}
            onKeyDown={(event) => {
              event.stopPropagation();
            }}
            aria-expanded={isExpanded}
            aria-label={isExpanded ? "Collapse services" : "Expand services"}
            style={{
              display: "grid",
              placeItems: "center",
              width: 28,
              height: 28,
              borderRadius: 6,
              border: "1px solid var(--rule)",
              background: isExpanded ? "var(--accent-soft)" : "transparent",
              cursor: "pointer",
              transition: "transform 0.15s ease",
            }}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{
                transform: isExpanded ? "rotate(180deg)" : "none",
                transition: "transform 0.15s ease",
              }}
            >
              <path d={I.chevronDown} />
            </svg>
          </button>
        </span>
      </div>

      {isExpanded && (
        <div
          style={{
            background: "var(--paper-alt)",
            borderBottom: "1px solid var(--rule)",
          }}
        >
          <div
            role="row"
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(160px, 1.4fr) repeat(4, minmax(80px, 1fr))",
              gap: 12,
              alignItems: "center",
              padding: "6px 16px 6px 48px",
              borderBottom: "1px solid var(--rule)",
              fontFamily: "var(--sans)",
              fontSize: 10.5,
              fontWeight: 650,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "var(--ink-3)",
            }}
          >
            <span>Service</span>
            <span style={{ textAlign: "right" }}>Score</span>
            <span style={{ textAlign: "right" }}>Archetype</span>
            <span style={{ textAlign: "right" }}>Difficulty</span>
            <span style={{ textAlign: "right" }}>Last scored</span>
          </div>
          {detailState?.status === "loading" || (needsFullServiceDetail && !detailState) ? (
            <ServicePanelMessage message="Loading service details..." />
          ) : detailState?.status === "error" ? (
            <ServicePanelMessage message={detailState.message} />
          ) : city.cached_scores.length === 0 ? (
            <ServicePanelMessage message="No cached service scores are available." />
          ) : (
            city.cached_scores.map((score) => {
              const serviceKey =
                (score.service || score.niche_normalized || "")
                  .trim()
                  .toLocaleLowerCase()
                  .replace(/[_-]+/g, " ");
              const isHighlighted =
                !!normalizedActiveService && serviceKey === normalizedActiveService;
              return (
                <ServiceDetailRow
                  key={score.report_id ?? score.service}
                  score={score}
                  isHighlighted={isHighlighted}
                />
              );
            })
          )}
        </div>
      )}
    </>
  );
}

function ServicePanelMessage({ message }: { message: string }) {
  return (
    <div
      role="row"
      style={{
        padding: "12px 16px 12px 48px",
        borderBottom: "1px solid var(--rule)",
        fontFamily: "var(--sans)",
        fontSize: 12.5,
        color: "var(--ink-3)",
      }}
    >
      {message}
    </div>
  );
}

export default function ExploreTable({
  cities,
  sortKey,
  sortDirection,
  activeService = "",
  detailStates = {},
  onCityExpand,
  onSortChange,
  onCityOpen,
  onReset,
}: ExploreTableProps) {
  const [expandedCities, setExpandedCities] = useState<Set<string>>(new Set());

  function toggleExpand(city: ExploreCitySummary) {
    setExpandedCities((prev) => {
      const next = new Set(prev);
      if (next.has(city.cbsa_code)) {
        next.delete(city.cbsa_code);
      } else {
        next.add(city.cbsa_code);
        onCityExpand(city);
      }
      return next;
    });
  }

  if (cities.length === 0) {
    return (
      <div
        role="status"
        style={{
          background: "var(--card)",
          border: "1px solid var(--rule)",
          borderRadius: 12,
          padding: "28px 20px",
          display: "grid",
          justifyItems: "center",
          gap: 12,
          textAlign: "center",
        }}
      >
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: 999,
            display: "grid",
            placeItems: "center",
            color: "var(--accent-ink)",
            background: "var(--accent-soft)",
          }}
        >
          <Icon d={I.search} size={17} />
        </div>
        <p
          style={{
            margin: 0,
            fontFamily: "var(--sans)",
            fontSize: 14,
            color: "var(--ink-2)",
          }}
        >
          No cities match the current filters.
        </p>
        <button
          type="button"
          className="btn-ghost"
          aria-label="Reset filters"
          onClick={onReset}
        >
          Reset filters
        </button>
      </div>
    );
  }

  return (
    <div
      role="table"
      aria-label="Explore cities"
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 12,
        overflowX: "auto",
      }}
    >
      <div style={{ minWidth: 960 }}>
        <div
          role="row"
          style={{
            display: "grid",
            gridTemplateColumns:
              "minmax(220px, 1.8fr) repeat(5, minmax(92px, 0.8fr)) minmax(72px, 0.6fr) 32px",
            gap: 12,
            alignItems: "center",
            padding: "10px 16px",
            background: "var(--paper-alt)",
            borderBottom: "1px solid var(--rule)",
          }}
        >
          {COLUMNS.map((column) => (
            <HeaderCell
              key={column.key}
              column={column}
              sortKey={sortKey}
              sortDirection={sortDirection}
              onSortChange={onSortChange}
            />
          ))}
          <span />
        </div>

        {cities.map((city) => (
          <CityRow
            key={city.cbsa_code}
            city={city}
            isExpanded={expandedCities.has(city.cbsa_code)}
            activeService={activeService}
            detailState={detailStates[city.cbsa_code]}
            onToggle={() => toggleExpand(city)}
            onCityOpen={() => onCityOpen(city)}
          />
        ))}
      </div>
    </div>
  );
}
