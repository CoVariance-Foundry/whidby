"use client";

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

export default function ExploreFilters({
  filters,
  states,
  services,
  growthAvailable,
  onChange,
  onReset,
}: ExploreFiltersProps) {
  function toggleState(state: string) {
    const selectedStates = filters.selectedStates.includes(state)
      ? filters.selectedStates.filter((item) => item !== state)
      : [...filters.selectedStates, state].sort();
    onChange(updateFilter(filters, { selectedStates }));
  }

  return (
    <section
      aria-label="Explore filters"
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 12,
        padding: 16,
        display: "grid",
        gap: 14,
      }}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
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
              value={filters.populationMin}
              onChange={(event) =>
                onChange(updateFilter(filters, { populationMin: event.target.value }))
              }
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
              value={filters.populationMax}
              onChange={(event) =>
                onChange(updateFilter(filters, { populationMax: event.target.value }))
              }
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
              value={filters.incomeMin}
              onChange={(event) =>
                onChange(updateFilter(filters, { incomeMin: event.target.value }))
              }
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
              value={filters.incomeMax}
              onChange={(event) =>
                onChange(updateFilter(filters, { incomeMax: event.target.value }))
              }
              placeholder="Any"
            />
          </div>
        </label>
        <label>
          <div className="field-label">Service</div>
          <select
            aria-label="Filter by cached service"
            value={filters.service}
            onChange={(event) =>
              onChange(updateFilter(filters, { service: event.target.value }))
            }
            style={{
              width: "100%",
              minHeight: 42,
              padding: "0 12px",
              border: "1px solid var(--rule-strong)",
              borderRadius: 8,
              background: "var(--card)",
              color: "var(--ink)",
              fontFamily: "var(--sans)",
              fontSize: 13,
            }}
          >
            <option value="">All cached services</option>
            {services.map((service) => (
              <option key={service} value={service}>
                {service}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div
        style={{
          display: "flex",
          gap: 12,
          alignItems: "flex-start",
          justifyContent: "space-between",
          flexWrap: "wrap",
        }}
      >
        <div
          role="group"
          aria-label="Filter by state"
          style={{
            display: "flex",
            gap: 7,
            flexWrap: "wrap",
            maxWidth: "min(100%, 760px)",
          }}
        >
          {states.map((state) => {
            const selected = filters.selectedStates.includes(state);
            return (
              <button
                key={state}
                type="button"
                aria-pressed={selected}
                onClick={() => toggleState(state)}
                style={{
                  minWidth: 42,
                  padding: "6px 10px",
                  borderRadius: 999,
                  border: `1px solid ${selected ? "var(--accent)" : "var(--rule)"}`,
                  background: selected ? "var(--accent-soft)" : "transparent",
                  color: selected ? "var(--accent-ink)" : "var(--ink-2)",
                  fontFamily: "var(--mono)",
                  fontSize: 12,
                  fontWeight: 600,
                }}
              >
                {state}
              </button>
            );
          })}
        </div>

        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <label
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              color: "var(--ink-2)",
              fontFamily: "var(--sans)",
              fontSize: 13,
              minHeight: 34,
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
