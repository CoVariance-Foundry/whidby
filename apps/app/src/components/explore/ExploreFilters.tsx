"use client";

import { type CSSProperties, type KeyboardEvent, useState } from "react";
import StateMultiselect from "@/components/StateMultiselect";
import { Icon, I } from "@/lib/icons";

export interface ExploreFilterState {
  populationMin: string;
  populationMax: string;
  incomeMin: string;
  incomeMax: string;
  selectedStates: string[];
  service: string;
  growingOnly: boolean;
}

interface ExploreFiltersProps {
  filters: ExploreFilterState;
  states: string[];
  services: string[];
  growthAvailable: boolean;
  onChange: (filters: ExploreFilterState) => void;
  onReset: () => void;
}

function updateFilter(
  filters: ExploreFilterState,
  patch: Partial<ExploreFilterState>,
): ExploreFilterState {
  return { ...filters, ...patch };
}

type NumericFilterKey =
  | "populationMin"
  | "populationMax"
  | "incomeMin"
  | "incomeMax";

function numericFilters(filters: ExploreFilterState): Pick<
  ExploreFilterState,
  NumericFilterKey
> {
  return {
    populationMin: filters.populationMin,
    populationMax: filters.populationMax,
    incomeMin: filters.incomeMin,
    incomeMax: filters.incomeMax,
  };
}

export default function ExploreFilters({
  filters,
  services,
  growthAvailable,
  onChange,
  onReset,
}: ExploreFiltersProps) {
  const [drafts, setDrafts] = useState(numericFilters(filters));

  function updateDraft(key: NumericFilterKey, value: string) {
    setDrafts((current) => ({ ...current, [key]: value }));
  }

  function commitDrafts(nextDrafts = drafts) {
    const current = numericFilters(filters);
    const changed = (Object.keys(nextDrafts) as NumericFilterKey[]).some(
      (key) => nextDrafts[key] !== current[key],
    );
    if (changed) {
      onChange(updateFilter(filters, nextDrafts));
    }
  }

  function commitOnEnter(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      commitDrafts();
      event.currentTarget.blur();
    }
  }

  const selectStyle: CSSProperties = {
    width: "100%",
    minHeight: 42,
    padding: "0 12px",
    border: "1px solid var(--rule-strong)",
    borderRadius: 8,
    background: "var(--card)",
    color: "var(--ink)",
    fontFamily: "var(--sans)",
    fontSize: 13,
  };

  return (
    <section
      aria-label="Explore filters"
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 12,
        padding: "16px 16px 14px",
        display: "grid",
        gap: 14,
      }}
    >
      {/* Row 1: Numeric range filters */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 12,
          alignItems: "end",
        }}
      >
        <label>
          <div className="field-label">Population min</div>
          <div className="input-wrap">
            <Icon d={I.filter} />
            <input
              aria-label="Minimum population"
              inputMode="numeric"
              value={drafts.populationMin}
              onChange={(event) => updateDraft("populationMin", event.target.value)}
              onBlur={() => commitDrafts()}
              onKeyDown={commitOnEnter}
              placeholder="Any"
            />
          </div>
        </label>
        <label>
          <div className="field-label">Population max</div>
          <div className="input-wrap">
            <Icon d={I.filter} />
            <input
              aria-label="Maximum population"
              inputMode="numeric"
              value={drafts.populationMax}
              onChange={(event) => updateDraft("populationMax", event.target.value)}
              onBlur={() => commitDrafts()}
              onKeyDown={commitOnEnter}
              placeholder="Any"
            />
          </div>
        </label>
        <label>
          <div className="field-label">Income min</div>
          <div className="input-wrap">
            <Icon d={I.target} />
            <input
              aria-label="Minimum median household income"
              inputMode="numeric"
              value={drafts.incomeMin}
              onChange={(event) => updateDraft("incomeMin", event.target.value)}
              onBlur={() => commitDrafts()}
              onKeyDown={commitOnEnter}
              placeholder="Any"
            />
          </div>
        </label>
        <label>
          <div className="field-label">Income max</div>
          <div className="input-wrap">
            <Icon d={I.target} />
            <input
              aria-label="Maximum median household income"
              inputMode="numeric"
              value={drafts.incomeMax}
              onChange={(event) => updateDraft("incomeMax", event.target.value)}
              onBlur={() => commitDrafts()}
              onKeyDown={commitOnEnter}
              placeholder="Any"
            />
          </div>
        </label>
      </div>

      {/* Row 2: States dropdown, Service select, Growing toggle, Reset */}
      <div
        style={{
          display: "flex",
          gap: 12,
          alignItems: "flex-end",
          flexWrap: "wrap",
        }}
      >
        <StateMultiselect
          label="States"
          selected={filters.selectedStates}
          onChange={(selectedStates) =>
            onChange(updateFilter(filters, { selectedStates }))
          }
        />

        <label style={{ minWidth: 180, flex: 1 }}>
          <div className="field-label">Service</div>
          <select
            aria-label="Filter by cached service"
            value={filters.service}
            onChange={(event) =>
              onChange(updateFilter(filters, { service: event.target.value }))
            }
            style={selectStyle}
          >
            <option value="">All cached services</option>
            {services.map((service) => (
              <option key={service} value={service}>
                {service}
              </option>
            ))}
          </select>
        </label>

        <div
          style={{
            display: "flex",
            gap: 10,
            alignItems: "center",
            alignSelf: "flex-end",
            minHeight: 42,
            flexWrap: "wrap",
          }}
        >
          <label
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              color: "var(--ink-2)",
              fontFamily: "var(--sans)",
              fontSize: 13,
              whiteSpace: "nowrap",
              opacity: growthAvailable ? 1 : 0.48,
            }}
          >
            <input
              type="checkbox"
              aria-label="Show growing markets only"
              checked={growthAvailable && filters.growingOnly}
              disabled={!growthAvailable}
              onChange={(event) =>
                onChange(updateFilter(filters, { growingOnly: event.target.checked }))
              }
              style={{ width: 16, height: 16, accentColor: "var(--accent)" }}
            />
            Growing markets only
          </label>
          <button
            type="button"
            className="btn-ghost"
            aria-label="Reset explore filters"
            onClick={onReset}
          >
            Reset
          </button>
        </div>
      </div>
    </section>
  );
}
