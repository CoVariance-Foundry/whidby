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
        } catch (err) {
          // AbortError is expected when the user keeps typing — swallow it.
          if (err instanceof DOMException && err.name === "AbortError") return;
          setSuggestions([]);
          setOpen(false);
          setHasFetched(false);
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
    <div className="relative w-full">
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
        className="w-full rounded-md border border-[var(--color-dark-border)] bg-[var(--color-dark)] px-3 py-2 text-sm"
      />

      {loading && (
        <span
          role="status"
          aria-live="polite"
          className="absolute right-2 top-2 text-xs text-[var(--color-muted)]"
        >
          …
        </span>
      )}

      {open && (
        <ul
          id={listboxId}
          role="listbox"
          aria-label="City suggestions"
          className="absolute z-50 mt-1 max-h-56 w-full overflow-auto rounded-md border border-[var(--color-dark-border)] bg-[var(--color-dark-card)] text-sm shadow-lg"
        >
          {hasFetched && suggestions.length === 0 ? (
            <li
              role="option"
              aria-disabled="true"
              aria-selected={false}
              className="cursor-default px-3 py-2 text-[var(--color-muted)]"
            >
              No metros match &ldquo;{value}&rdquo;
            </li>
          ) : (
            suggestions.map((s, i) => (
              <li
                key={`${s.city}-${s.region ?? "na"}-${s.country}-${i}`}
                id={`${listboxId}-option-${i}`}
                role="option"
                aria-selected={i === activeIndex}
                onMouseDown={() => selectSuggestion(s)}
                className={[
                  "cursor-pointer px-3 py-2",
                  i === activeIndex
                    ? "bg-[var(--color-accent)] text-white"
                    : "hover:bg-[var(--color-dark-hover)]",
                ].join(" ")}
              >
                <span className="font-medium">{s.city}</span>
                <span className="ml-1 text-[var(--color-muted)]">
                  {s.region ?? s.country}
                </span>
                {s.region && (
                  <span className="ml-auto block text-xs text-[var(--color-muted)]">
                    {s.country}
                  </span>
                )}
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
