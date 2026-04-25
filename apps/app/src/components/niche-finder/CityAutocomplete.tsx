// Mirror of apps/admin/src/components/niche-finder/CityAutocomplete.tsx.
// Keep behavior in sync until lifted to packages/.
// Restyled for the consumer light academic theme — no dark Tailwind classes.

"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import {
  fetchPlaceSuggestions,
  formatPlaceSuggestion,
  type PlaceSuggestion,
} from "@/lib/niche-finder/place-suggest";

const DEFAULT_DEBOUNCE_MS = 250;

interface CityAutocompleteProps {
  value: string;
  onChange: (city: string, suggestion?: PlaceSuggestion) => void;
  disabled?: boolean;
  placeholder?: string;
  /** data-testid forwarded to the underlying <input> */
  "data-testid"?: string;
  /**
   * Debounce delay in ms before triggering a fetch.
   * Primarily exists as an escape hatch for tests (pass 0 to skip debounce).
   * @default 250
   */
  debounceMs?: number;
}

export default function CityAutocomplete({
  value,
  onChange,
  disabled = false,
  placeholder = "City (e.g. Phoenix)",
  "data-testid": testId = "city-input",
  debounceMs = DEFAULT_DEBOUNCE_MS,
}: CityAutocompleteProps) {
  const [suggestions, setSuggestions] = useState<PlaceSuggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [loading, setLoading] = useState(false);
  const [hasFetched, setHasFetched] = useState(false);
  const [fetchError, setFetchError] = useState(false);

  const listboxId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /** Cancel any pending debounced fetch and in-flight request. */
  const cancel = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, []);

  useEffect(() => cancel, [cancel]);

  const fetchSuggestions = useCallback(
    (q: string) => {
      cancel();

      if (q.trim().length < 2) {
        setSuggestions([]);
        setOpen(false);
        setHasFetched(false);
        return;
      }

      timerRef.current = setTimeout(async () => {
        const controller = new AbortController();
        abortRef.current = controller;
        setLoading(true);

        try {
          const results = await fetchPlaceSuggestions(q, 8, controller.signal);
          setSuggestions(results);
          setOpen(true);
          setHasFetched(true);
          setActiveIndex(-1);
          setFetchError(false);
        } catch (err) {
          if (err instanceof DOMException && err.name === "AbortError") return;
          setSuggestions([]);
          setOpen(false);
          setHasFetched(false);
          setFetchError(true);
        } finally {
          setLoading(false);
        }
      }, debounceMs);
    },
    [cancel, debounceMs],
  );

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const q = e.target.value;
    onChange(q);
    fetchSuggestions(q);
  };

  const selectSuggestion = (suggestion: PlaceSuggestion) => {
    cancel();
    onChange(formatPlaceSuggestion(suggestion), suggestion);
    setSuggestions([]);
    setOpen(false);
    setActiveIndex(-1);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!open) return;

    // When the only row is the disabled empty-state, only Escape is handled.
    if (suggestions.length === 0) {
      if (e.key === "Escape") {
        setOpen(false);
        setActiveIndex(-1);
      }
      return;
    }

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setActiveIndex((prev) => Math.min(prev + 1, suggestions.length - 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setActiveIndex((prev) => Math.max(prev - 1, 0));
        break;
      case "Enter":
        e.preventDefault();
        if (activeIndex >= 0 && activeIndex < suggestions.length) {
          selectSuggestion(suggestions[activeIndex]);
        }
        break;
      case "Escape":
        setOpen(false);
        setActiveIndex(-1);
        break;
      default:
        break;
    }
  };

  const handleBlur = () => {
    // Delay so click on a suggestion option fires first.
    setTimeout(() => {
      setOpen(false);
      setActiveIndex(-1);
    }, 150);
  };

  return (
    <div style={{ position: "relative", width: "100%" }}>
      <div className="input-wrap">
        <input
          ref={inputRef}
          data-testid={testId}
          type="text"
          value={value}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          disabled={disabled}
          placeholder={placeholder}
          autoComplete="off"
          role="combobox"
          aria-expanded={open}
          aria-haspopup="listbox"
          aria-autocomplete="list"
          aria-controls={listboxId}
          aria-activedescendant={
            activeIndex >= 0 ? `${listboxId}-option-${activeIndex}` : undefined
          }
          style={{ flex: 1 }}
        />
        {loading && (
          <span
            role="status"
            aria-live="polite"
            style={{
              fontSize: 11,
              color: "var(--ink-3)",
              fontFamily: "var(--mono)",
              flexShrink: 0,
            }}
          >
            …
          </span>
        )}
      </div>

      {fetchError && !open && (
        <div
          style={{
            marginTop: 4,
            fontSize: 11.5,
            fontFamily: "var(--serif)",
            fontStyle: "italic",
            color: "var(--ink-3)",
          }}
        >
          City suggestions unavailable — try again shortly
        </div>
      )}

      {open && (
        <ul
          id={listboxId}
          role="listbox"
          aria-label="City suggestions"
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            left: 0,
            right: 0,
            zIndex: 50,
            maxHeight: 224,
            overflowY: "auto",
            background: "var(--card)",
            border: "1px solid var(--rule-strong)",
            borderRadius: 8,
            boxShadow: "0 4px 16px rgba(31,27,22,0.10)",
            padding: 0,
            margin: 0,
            listStyle: "none",
          }}
        >
          {hasFetched && suggestions.length === 0 ? (
            <li
              role="option"
              aria-disabled="true"
              aria-selected={false}
              style={{
                padding: "10px 14px",
                fontFamily: "var(--serif)",
                fontStyle: "italic",
                fontSize: 13,
                color: "var(--ink-3)",
                cursor: "default",
              }}
            >
              No metros match &ldquo;{value}&rdquo;
            </li>
          ) : (
            suggestions.map((s, i) => {
              const isActive = i === activeIndex;
              return (
                <li
                  key={`${s.city}-${s.region ?? "na"}-${s.country}-${i}`}
                  id={`${listboxId}-option-${i}`}
                  role="option"
                  aria-selected={isActive}
                  onMouseDown={() => selectSuggestion(s)}
                  style={{
                    padding: "10px 14px",
                    cursor: "pointer",
                    borderBottom: i < suggestions.length - 1 ? "1px solid var(--rule)" : "none",
                    background: isActive ? "var(--accent-soft)" : "transparent",
                    transition: "background 0.1s",
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      (e.currentTarget as HTMLElement).style.background = "var(--hover)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      (e.currentTarget as HTMLElement).style.background = "transparent";
                    }
                  }}
                >
                  <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
                    <span
                      style={{
                        fontFamily: "var(--serif)",
                        fontWeight: 600,
                        fontSize: 14,
                        color: isActive ? "var(--accent-ink)" : "var(--ink)",
                      }}
                    >
                      {s.city}
                    </span>
                    <span
                      style={{
                        fontSize: 12,
                        color: "var(--ink-3)",
                        fontFamily: "var(--mono)",
                      }}
                    >
                      {s.region ?? s.country}
                    </span>
                  </div>
                  {s.region && (
                    <div
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 11,
                        color: "var(--ink-3)",
                        marginTop: 2,
                        letterSpacing: "0.01em",
                      }}
                    >
                      {s.country}
                    </div>
                  )}
                </li>
              );
            })
          )}
        </ul>
      )}
    </div>
  );
}
