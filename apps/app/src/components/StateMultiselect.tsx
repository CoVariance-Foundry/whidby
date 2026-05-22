"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Icon, I } from "@/lib/icons";

interface StateOption {
  abbr: string;
  name: string;
}

interface StateRegion {
  name: string;
  states: StateOption[];
}

const REGIONS: StateRegion[] = [
  {
    name: "Northeast",
    states: [
      { abbr: "CT", name: "Connecticut" },
      { abbr: "DE", name: "Delaware" },
      { abbr: "DC", name: "D.C." },
      { abbr: "ME", name: "Maine" },
      { abbr: "MD", name: "Maryland" },
      { abbr: "MA", name: "Massachusetts" },
      { abbr: "NH", name: "New Hampshire" },
      { abbr: "NJ", name: "New Jersey" },
      { abbr: "NY", name: "New York" },
      { abbr: "PA", name: "Pennsylvania" },
      { abbr: "RI", name: "Rhode Island" },
      { abbr: "VT", name: "Vermont" },
    ],
  },
  {
    name: "Midwest",
    states: [
      { abbr: "IL", name: "Illinois" },
      { abbr: "IN", name: "Indiana" },
      { abbr: "IA", name: "Iowa" },
      { abbr: "KS", name: "Kansas" },
      { abbr: "MI", name: "Michigan" },
      { abbr: "MN", name: "Minnesota" },
      { abbr: "MO", name: "Missouri" },
      { abbr: "NE", name: "Nebraska" },
      { abbr: "ND", name: "North Dakota" },
      { abbr: "OH", name: "Ohio" },
      { abbr: "SD", name: "South Dakota" },
      { abbr: "WI", name: "Wisconsin" },
    ],
  },
  {
    name: "South",
    states: [
      { abbr: "AL", name: "Alabama" },
      { abbr: "AR", name: "Arkansas" },
      { abbr: "FL", name: "Florida" },
      { abbr: "GA", name: "Georgia" },
      { abbr: "KY", name: "Kentucky" },
      { abbr: "LA", name: "Louisiana" },
      { abbr: "MS", name: "Mississippi" },
      { abbr: "NC", name: "North Carolina" },
      { abbr: "OK", name: "Oklahoma" },
      { abbr: "SC", name: "South Carolina" },
      { abbr: "TN", name: "Tennessee" },
      { abbr: "TX", name: "Texas" },
      { abbr: "VA", name: "Virginia" },
      { abbr: "WV", name: "West Virginia" },
    ],
  },
  {
    name: "West",
    states: [
      { abbr: "AK", name: "Alaska" },
      { abbr: "AZ", name: "Arizona" },
      { abbr: "CA", name: "California" },
      { abbr: "CO", name: "Colorado" },
      { abbr: "HI", name: "Hawaii" },
      { abbr: "ID", name: "Idaho" },
      { abbr: "MT", name: "Montana" },
      { abbr: "NV", name: "Nevada" },
      { abbr: "NM", name: "New Mexico" },
      { abbr: "OR", name: "Oregon" },
      { abbr: "UT", name: "Utah" },
      { abbr: "WA", name: "Washington" },
      { abbr: "WY", name: "Wyoming" },
    ],
  },
  {
    name: "Territories",
    states: [{ abbr: "PR", name: "Puerto Rico" }],
  },
];

const ALL_STATES = REGIONS.flatMap((region) => region.states);

interface StateMultiselectProps {
  selected: string[];
  onChange: (abbrs: string[]) => void;
  availableAbbrs?: string[];
  label?: string;
  placeholder?: string;
}

function selectedLabel(selected: string[], placeholder: string) {
  if (selected.length === 0) return placeholder;
  if (selected.length === 1) {
    return ALL_STATES.find((state) => state.abbr === selected[0])?.name ?? selected[0];
  }
  if (selected.length <= 3) return selected.join(", ");
  return `${selected.length} states selected`;
}

export default function StateMultiselect({
  selected,
  onChange,
  availableAbbrs,
  label,
  placeholder = "All states",
}: StateMultiselectProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const availableSet = useMemo(() => {
    const normalizedAbbrs = availableAbbrs?.filter(Boolean) ?? [];
    return normalizedAbbrs.length > 0 ? new Set(normalizedAbbrs) : null;
  }, [availableAbbrs]);

  useEffect(() => {
    if (!open) return;

    function onDocumentMouseDown(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
        setQuery("");
      }
    }

    function onDocumentKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        setQuery("");
      }
    }

    document.addEventListener("mousedown", onDocumentMouseDown);
    document.addEventListener("keydown", onDocumentKeyDown);
    searchRef.current?.focus();
    return () => {
      document.removeEventListener("mousedown", onDocumentMouseDown);
      document.removeEventListener("keydown", onDocumentKeyDown);
    };
  }, [open]);

  const filteredRegions = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return REGIONS;

    return REGIONS.map((region) => ({
      ...region,
      states: region.states.filter(
        (state) =>
          state.name.toLowerCase().includes(normalizedQuery) ||
          state.abbr.toLowerCase().includes(normalizedQuery),
      ),
    })).filter((region) => region.states.length > 0);
  }, [query]);

  function selectable(abbr: string) {
    return !availableSet || availableSet.has(abbr);
  }

  function toggleState(abbr: string) {
    onChange(
      selected.includes(abbr)
        ? selected.filter((state) => state !== abbr)
        : [...selected, abbr].sort(),
    );
  }

  function toggleRegion(abbrs: string[]) {
    const targets = abbrs.filter(selectable);
    const allSelected = targets.length > 0 && targets.every((abbr) => selected.includes(abbr));
    onChange(
      allSelected
        ? selected.filter((abbr) => !targets.includes(abbr))
        : Array.from(new Set([...selected, ...targets])).sort(),
    );
  }

  return (
    <div ref={rootRef} style={{ position: "relative", minWidth: 220, flex: "1 1 220px" }}>
      {label ? <div className="field-label">{label}</div> : null}
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-label={label ? `Select ${label.toLowerCase()}` : "Select states"}
        onClick={() => setOpen((current) => !current)}
        style={{
          width: "100%",
          minHeight: 42,
          padding: "6px 10px",
          display: "flex",
          alignItems: "center",
          gap: 8,
          background: "var(--card)",
          border: `1px solid ${open ? "var(--accent)" : "var(--rule-strong)"}`,
          borderRadius: 8,
          boxShadow: open ? "0 0 0 3px var(--accent-soft)" : "none",
          color: selected.length > 0 ? "var(--ink)" : "var(--ink-3)",
          fontSize: 14,
          textAlign: "left",
        }}
      >
        <span style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {selectedLabel(selected, placeholder)}
        </span>
        {selected.length > 0 ? (
          <span
            style={{
              borderRadius: 999,
              background: "var(--accent-soft)",
              color: "var(--accent-ink)",
              fontFamily: "var(--mono)",
              fontSize: 11,
              fontWeight: 700,
              padding: "2px 7px",
            }}
          >
            {selected.length}
          </span>
        ) : null}
        <Icon d={I.chevronDown} style={{ transform: open ? "rotate(180deg)" : undefined }} />
      </button>

      {open ? (
        <div
          role="listbox"
          aria-multiselectable="true"
          aria-label="State selection"
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            left: 0,
            zIndex: 60,
            width: "min(560px, 92vw)",
            maxWidth: "92vw",
            padding: 12,
            border: "1px solid var(--rule-strong)",
            borderRadius: 10,
            background: "var(--card)",
            boxShadow: "0 18px 44px rgba(47, 38, 20, 0.18)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 10px",
              border: "1px solid var(--rule)",
              borderRadius: 8,
              background: "var(--paper)",
            }}
          >
            <Icon d={I.search} />
            <input
              ref={searchRef}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search states"
              aria-label="Search states"
              style={{
                flex: 1,
                minWidth: 0,
                border: 0,
                outline: "none",
                background: "transparent",
                color: "var(--ink)",
                fontSize: 13,
              }}
            />
            {selected.length > 0 ? (
              <button
                type="button"
                onClick={() => onChange([])}
                style={{
                  padding: "4px 8px",
                  borderRadius: 6,
                  background: "var(--danger-soft)",
                  color: "var(--danger)",
                  fontSize: 11,
                  fontWeight: 700,
                }}
              >
                Clear
              </button>
            ) : null}
          </div>

          <div style={{ maxHeight: 360, overflowY: "auto", marginTop: 12, display: "grid", gap: 12 }}>
            {filteredRegions.length === 0 ? (
              <p style={{ margin: 0, padding: 16, color: "var(--ink-3)", fontSize: 13 }}>
                No states match &quot;{query}&quot;.
              </p>
            ) : null}
            {filteredRegions.map((region) => {
              const regionAbbrs = region.states.map((state) => state.abbr);
              const selectableAbbrs = regionAbbrs.filter(selectable);
              const allSelected =
                selectableAbbrs.length > 0 &&
                selectableAbbrs.every((abbr) => selected.includes(abbr));

              return (
                <section key={region.name} aria-label={region.name}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: 10,
                      marginBottom: 6,
                    }}
                  >
                    <p
                      style={{
                        margin: 0,
                        color: "var(--ink-3)",
                        fontSize: 11,
                        fontWeight: 700,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                      }}
                    >
                      {region.name}
                    </p>
                    {selectableAbbrs.length > 0 ? (
                      <button
                        type="button"
                        onClick={() => toggleRegion(regionAbbrs)}
                        style={{
                          color: "var(--accent-ink)",
                          fontSize: 11,
                          fontWeight: 700,
                          textDecoration: "underline",
                          textUnderlineOffset: 2,
                        }}
                      >
                        {allSelected ? "Deselect region" : "Select region"}
                      </button>
                    ) : null}
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 4 }}>
                    {region.states.map((state) => {
                      const isSelected = selected.includes(state.abbr);
                      const isSelectable = selectable(state.abbr);
                      return (
                        <button
                          key={state.abbr}
                          type="button"
                          role="option"
                          aria-label={`${state.abbr} ${state.name}`}
                          aria-selected={isSelected}
                          disabled={!isSelectable}
                          onClick={() => toggleState(state.abbr)}
                          style={{
                            minWidth: 0,
                            display: "grid",
                            gridTemplateColumns: "18px 32px minmax(0, 1fr)",
                            alignItems: "center",
                            gap: 8,
                            padding: "7px 8px",
                            borderRadius: 7,
                            color: !isSelectable
                              ? "var(--ink-3)"
                              : isSelected
                                ? "var(--accent-ink)"
                                : "var(--ink)",
                            background: isSelected ? "var(--accent-soft)" : "transparent",
                            opacity: isSelectable ? 1 : 0.42,
                            fontSize: 13,
                            textAlign: "left",
                          }}
                        >
                          <span
                            aria-hidden="true"
                            style={{
                              width: 16,
                              height: 16,
                              borderRadius: 4,
                              display: "grid",
                              placeItems: "center",
                              border: `1.5px solid ${isSelected ? "var(--accent)" : "var(--rule-strong)"}`,
                              background: isSelected ? "var(--accent)" : "var(--card)",
                              color: "white",
                            }}
                          >
                            {isSelected ? <Icon d={I.check} size={10} sw={3} /> : null}
                          </span>
                          <span style={{ fontFamily: "var(--mono)", fontSize: 11, fontWeight: 700 }}>
                            {state.abbr}
                          </span>
                          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {state.name}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </section>
              );
            })}
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 10,
              marginTop: 12,
              paddingTop: 10,
              borderTop: "1px solid var(--rule)",
            }}
          >
            <span style={{ color: "var(--ink-2)", fontSize: 12 }}>
              <strong style={{ color: "var(--ink)", fontFamily: "var(--mono)" }}>{selected.length}</strong>{" "}
              selected
            </span>
            <button
              type="button"
              className="btn-primary"
              onClick={() => {
                setOpen(false);
                setQuery("");
              }}
            >
              Done
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
