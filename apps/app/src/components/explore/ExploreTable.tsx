"use client";

import type { ExploreCitySummary } from "@/lib/explore/types";
import { Icon, I } from "@/lib/icons";
import { formatCurrency, formatDecimal, formatInteger, formatPercent } from "./format";

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
  onSortChange: (key: ExploreSortKey) => void;
  onCityOpen: (city: ExploreCitySummary) => void;
  onReset: () => void;
}

const COLUMNS: Array<{ key: ExploreSortKey; label: string; align?: "right" }> = [
  { key: "city", label: "City" },
  { key: "population", label: "Population", align: "right" },
  { key: "income", label: "Income", align: "right" },
  { key: "business_density", label: "Density", align: "right" },
  { key: "growth", label: "Growth", align: "right" },
  { key: "cached_services", label: "Cached", align: "right" },
  { key: "best_opportunity", label: "Best", align: "right" },
];

function SortIcon({
  active,
  direction,
}: {
  active: boolean;
  direction: SortDirection;
}) {
  if (!active) {
    return <Icon d={I.chevronDown} size={12} style={{ opacity: 0.35 }} />;
  }
  return <Icon d={direction === "asc" ? I.arrowUp : I.arrowDown} size={12} />;
}

function headerCell(
  column: (typeof COLUMNS)[number],
  sortKey: ExploreSortKey,
  sortDirection: SortDirection,
  onSortChange: (key: ExploreSortKey) => void,
) {
  const active = sortKey === column.key;
  return (
    <span
      key={column.key}
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

export default function ExploreTable({
  cities,
  sortKey,
  sortDirection,
  onSortChange,
  onCityOpen,
  onReset,
}: ExploreTableProps) {
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
      <div style={{ minWidth: 920 }}>
        <div
          role="row"
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(220px, 1.8fr) repeat(6, minmax(92px, 0.8fr))",
            gap: 12,
            alignItems: "center",
            padding: "10px 16px",
            background: "var(--paper-alt)",
            borderBottom: "1px solid var(--rule)",
          }}
        >
          {COLUMNS.map((column) =>
            headerCell(column, sortKey, sortDirection, onSortChange),
          )}
        </div>

        {cities.map((city) => (
          <div
            key={city.cbsa_code}
            role="row"
            tabIndex={0}
            className="report-row-clickable"
            aria-label={`Open ${city.cbsa_name}`}
            onClick={() => onCityOpen(city)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onCityOpen(city);
              }
            }}
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(220px, 1.8fr) repeat(6, minmax(92px, 0.8fr))",
              gap: 12,
              alignItems: "center",
              padding: "13px 16px",
              borderBottom: "1px solid var(--rule)",
              cursor: "pointer",
              fontFamily: "var(--sans)",
              fontSize: 13.5,
              color: "var(--ink)",
            }}
          >
            <span role="cell" style={{ minWidth: 0 }}>
              <span
                style={{
                  display: "block",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  fontWeight: 650,
                }}
              >
                {city.cbsa_name}
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
            <span role="cell" style={{ textAlign: "right", fontFamily: "var(--mono)" }}>
              {city.cached_services_count}
            </span>
            <span
              role="cell"
              style={{
                textAlign: "right",
                fontFamily: "var(--mono)",
                color: "var(--accent-ink)",
                fontWeight: 700,
              }}
            >
              {city.best_opportunity_score ?? "-"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
