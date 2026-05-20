"use client";

import { type KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import { Icon, I } from "@/lib/icons";

const US_STATES = [
  "AK","AL","AR","AZ","CA","CO","CT","DC","DE","FL","GA","HI","IA","ID","IL",
  "IN","KS","KY","LA","MA","MD","ME","MI","MN","MO","MS","MT","NC","ND","NE",
  "NH","NJ","NM","NV","NY","OH","OK","OR","PA","PR","RI","SC","SD","TN","TX",
  "UT","VA","VT","WA","WI","WV","WY",
];

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

function StateMultiSelect({
  states,
  selected,
  onToggle,
  onClear,
}: {
  states: string[];
  selected: string[];
  onToggle: (state: string) => void;
  onClear: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const allStates = useMemo(() => {
    const merged = new Set([...US_STATES, ...states, ...selected]);
    return [...merged].sort();
  }, [states, selected]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
        setSearch("");
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [open]);

  useEffect(() => {
    if (open && searchRef.current) {
      searchRef.current.focus();
    }
  }, [open]);

  const filtered = search
    ? allStates.filter((s) => s.toLowerCase().includes(search.toLowerCase()))
    : allStates;

  return (
    <div ref={containerRef} style={{ position: "relative", minWidth: 200, flex: 1 }}>
      <div className="field-label">States</div>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-label="Filter by state"
        style={{
          width: "100%",
          minHeight: 42,
          padding: "6px 10px",
          display: "flex",
          alignItems: "center",
          gap: 6,
          flexWrap: "wrap",
          background: "var(--card)",
          border: `1px solid ${open ? "var(--accent)" : "var(--rule-strong)"}`,
          borderRadius: 8,
          cursor: "pointer",
          textAlign: "left",
          boxShadow: open ? "0 0 0 3px var(--accent-soft)" : "none",
          transition: "border-color 0.15s, box-shadow 0.15s",
        }}
      >
        {selected.length === 0 ? (
          <span
            style={{
              color: "var(--ink-3)",
              fontFamily: "var(--sans)",
              fontSize: 14,
              flex: 1,
            }}
          >
            All states
          </span>
        ) : (
          <>
            <span style={{ display: "contents" }}>
              {selected.slice(0, 6).map((state) => (
                <span
                  key={state}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 3,
                    padding: "2px 6px 2px 8px",
                    borderRadius: 4,
                    background: "var(--accent-soft)",
                    color: "var(--accent-ink)",
                    fontFamily: "var(--mono)",
                    fontSize: 11,
                    fontWeight: 600,
                    lineHeight: 1.5,
                    whiteSpace: "nowrap",
                  }}
                >
                  {state}
                  <span
                    role="button"
                    tabIndex={0}
                    aria-label={`Remove ${state}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggle(state);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.stopPropagation();
                        onToggle(state);
                      }
                    }}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      width: 14,
                      height: 14,
                      borderRadius: 3,
                      cursor: "pointer",
                      opacity: 0.6,
                    }}
                  >
                    <Icon d={I.x} />
                  </span>
                </span>
              ))}
            </span>
            {selected.length > 6 && (
              <span
                style={{
                  fontFamily: "var(--sans)",
                  fontSize: 11,
                  color: "var(--ink-3)",
                  fontWeight: 500,
                }}
              >
                +{selected.length - 6}
              </span>
            )}
            <span style={{ flex: 1 }} />
          </>
        )}
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{
            flexShrink: 0,
            color: "var(--ink-3)",
            transform: open ? "rotate(180deg)" : "none",
            transition: "transform 0.15s ease",
          }}
        >
          <path d={I.chevronDown} />
        </svg>
      </button>

      {open && (
        <div
          role="listbox"
          aria-multiselectable="true"
          aria-label="State selection"
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            left: 0,
            right: 0,
            background: "var(--card)",
            border: "1px solid var(--rule-strong)",
            borderRadius: 10,
            boxShadow:
              "0 8px 24px rgba(31, 27, 22, 0.1), 0 2px 8px rgba(31, 27, 22, 0.06)",
            zIndex: 50,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "8px 8px 4px",
              borderBottom: "1px solid var(--rule)",
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <div
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "0 6px",
              }}
            >
              <Icon d={I.search} />
              <input
                ref={searchRef}
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search states..."
                aria-label="Search states"
                style={{
                  flex: 1,
                  border: "none",
                  outline: "none",
                  background: "transparent",
                  fontFamily: "var(--sans)",
                  fontSize: 13,
                  color: "var(--ink)",
                  padding: "6px 0",
                }}
              />
            </div>
            {selected.length > 0 && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onClear();
                }}
                style={{
                  padding: "4px 8px",
                  borderRadius: 5,
                  border: "none",
                  background: "var(--danger-soft)",
                  color: "var(--danger)",
                  fontFamily: "var(--sans)",
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                }}
              >
                Clear ({selected.length})
              </button>
            )}
          </div>

          <div
            style={{
              maxHeight: 220,
              overflowY: "auto",
              padding: "4px 0",
            }}
          >
            {filtered.length === 0 ? (
              <div
                style={{
                  padding: "12px 14px",
                  fontFamily: "var(--serif)",
                  fontStyle: "italic",
                  fontSize: 13,
                  color: "var(--ink-3)",
                }}
              >
                No states match &ldquo;{search}&rdquo;
              </div>
            ) : (
              filtered.map((state) => {
                const isSelected = selected.includes(state);
                return (
                  <button
                    key={state}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => onToggle(state)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      width: "100%",
                      padding: "7px 12px",
                      border: "none",
                      background: isSelected
                        ? "var(--accent-soft)"
                        : "transparent",
                      cursor: "pointer",
                      fontFamily: "var(--sans)",
                      fontSize: 13,
                      color: isSelected ? "var(--accent-ink)" : "var(--ink)",
                      textAlign: "left",
                      transition: "background 0.1s",
                    }}
                    onMouseEnter={(e) => {
                      if (!isSelected)
                        e.currentTarget.style.background = "var(--hover)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = isSelected
                        ? "var(--accent-soft)"
                        : "transparent";
                    }}
                  >
                    <span
                      style={{
                        width: 16,
                        height: 16,
                        borderRadius: 4,
                        border: `1.5px solid ${isSelected ? "var(--accent)" : "var(--rule-strong)"}`,
                        background: isSelected ? "var(--accent)" : "var(--card)",
                        display: "grid",
                        placeItems: "center",
                        flexShrink: 0,
                        transition: "all 0.1s",
                      }}
                    >
                      {isSelected && (
                        <svg
                          width="10"
                          height="10"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="white"
                          strokeWidth="3"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d={I.check} />
                        </svg>
                      )}
                    </span>
                    <span
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 12,
                        fontWeight: 600,
                        width: 22,
                      }}
                    >
                      {state}
                    </span>
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ExploreFilters({
  filters,
  states,
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

  function toggleState(state: string) {
    const selectedStates = filters.selectedStates.includes(state)
      ? filters.selectedStates.filter((item) => item !== state)
      : [...filters.selectedStates, state].sort();
    onChange(updateFilter(filters, { selectedStates }));
  }

  function clearStates() {
    onChange(updateFilter(filters, { selectedStates: [] }));
  }

  const selectStyle: React.CSSProperties = {
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
        <StateMultiSelect
          states={states}
          selected={filters.selectedStates}
          onToggle={toggleState}
          onClear={clearStates}
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
