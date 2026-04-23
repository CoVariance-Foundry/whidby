// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent, act } from "@testing-library/react";
import ExplorationQueryForm from "./ExplorationQueryForm";
import type { NicheQueryInput } from "@/lib/niche-finder/types";
import type { PlaceSuggestion } from "@/lib/niche-finder/place-suggest";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------
const DALLAS_SUGGESTION: PlaceSuggestion = {
  city: "Dallas",
  region: "TX",
  country: "US",
  place_id: "place.dallas",
  dataforseo_location_code: 1026339,
};

const INITIAL_QUERY: NicheQueryInput = { city: "", service: "" };

// ---------------------------------------------------------------------------
// Mock CityAutocomplete — same pattern as StandardNicheForm.test.tsx.
// Captures the onChange callback so tests can trigger both free-text changes
// and suggestion selections directly.
// ---------------------------------------------------------------------------
let capturedOnChange: ((city: string, suggestion?: PlaceSuggestion) => void) | null = null;

vi.mock("@/components/niche-finder/CityAutocomplete", () => ({
  default: ({
    value,
    onChange,
    disabled,
    "data-testid": testId,
  }: {
    value: string;
    onChange: (city: string, suggestion?: PlaceSuggestion) => void;
    disabled?: boolean;
    "data-testid"?: string;
  }) => {
    capturedOnChange = onChange;
    return (
      <input
        data-testid={testId ?? "city-input"}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  },
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  capturedOnChange = null;
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe("ExplorationQueryForm", () => {
  it("renders explore-city-input, explore-service-input, and submit button", () => {
    render(<ExplorationQueryForm initialQuery={INITIAL_QUERY} onSubmit={vi.fn()} />);
    expect(screen.getByTestId("explore-city-input")).toBeInTheDocument();
    expect(screen.getByTestId("explore-service-input")).toBeInTheDocument();
    expect(screen.getByTestId("explore-btn")).toBeInTheDocument();
  });

  it("selecting a suggestion populates both city and state on submit", () => {
    const onSubmit = vi.fn();
    render(<ExplorationQueryForm initialQuery={INITIAL_QUERY} onSubmit={onSubmit} />);

    // Simulate the user picking Dallas from the dropdown
    act(() => {
      capturedOnChange!("Dallas, TX", DALLAS_SUGGESTION);
    });

    fireEvent.change(screen.getByTestId("explore-service-input"), {
      target: { value: "landscaping" },
    });

    fireEvent.submit(screen.getByTestId("explore-btn").closest("form")!);

    expect(onSubmit).toHaveBeenCalledOnce();
    const submitted: NicheQueryInput = onSubmit.mock.calls[0][0];
    expect(submitted.city).toBe("Dallas");
    expect(submitted.state).toBe("TX");
    expect(submitted.service).toBe("landscaping");
    expect(submitted.place_id).toBe("place.dallas");
    expect(submitted.dataforseo_location_code).toBe(1026339);
  });

  it("editing city after selecting a suggestion clears state", () => {
    const onSubmit = vi.fn();
    render(<ExplorationQueryForm initialQuery={INITIAL_QUERY} onSubmit={onSubmit} />);

    // First select a suggestion
    act(() => {
      capturedOnChange!("Dallas, TX", DALLAS_SUGGESTION);
    });

    // Then free-type a different city — state should be cleared
    fireEvent.change(screen.getByTestId("explore-city-input"), {
      target: { value: "Fort Worth" },
    });

    fireEvent.change(screen.getByTestId("explore-service-input"), {
      target: { value: "landscaping" },
    });

    fireEvent.submit(screen.getByTestId("explore-btn").closest("form")!);

    expect(onSubmit).toHaveBeenCalledOnce();
    const submitted: NicheQueryInput = onSubmit.mock.calls[0][0];
    expect(submitted.city).toBe("Fort Worth");
    expect(submitted.state).toBeUndefined();
    expect(submitted.place_id).toBeUndefined();
    expect(submitted.dataforseo_location_code).toBeUndefined();
  });

  it("submitting with only free-typed city sends state: undefined", () => {
    const onSubmit = vi.fn();
    render(<ExplorationQueryForm initialQuery={INITIAL_QUERY} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByTestId("explore-city-input"), {
      target: { value: "Houston" },
    });
    fireEvent.change(screen.getByTestId("explore-service-input"), {
      target: { value: "hvac" },
    });

    fireEvent.submit(screen.getByTestId("explore-btn").closest("form")!);

    expect(onSubmit).toHaveBeenCalledOnce();
    const submitted: NicheQueryInput = onSubmit.mock.calls[0][0];
    expect(submitted.city).toBe("Houston");
    expect(submitted.service).toBe("hvac");
    expect(submitted.state).toBeUndefined();
  });

  it("is disabled when disabled prop is true", () => {
    render(
      <ExplorationQueryForm
        initialQuery={INITIAL_QUERY}
        onSubmit={vi.fn()}
        disabled={true}
      />,
    );
    expect(screen.getByTestId("explore-city-input")).toBeDisabled();
    expect(screen.getByTestId("explore-service-input")).toBeDisabled();
    expect(screen.getByTestId("explore-btn")).toBeDisabled();
  });
});
