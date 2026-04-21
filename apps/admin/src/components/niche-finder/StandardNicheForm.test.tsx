// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent, act } from "@testing-library/react";
import StandardNicheForm from "./StandardNicheForm";
import type { NicheQueryInput } from "@/lib/niche-finder/types";
import type { MetroSuggestion } from "@/lib/niche-finder/metro-suggest";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------
const PHOENIX_SUGGESTION: MetroSuggestion = {
  cbsa_code: "38060",
  city: "Phoenix",
  state: "AZ",
  cbsa_name: "Phoenix-Mesa-Chandler, AZ",
  population: 4946145,
};

const INITIAL_QUERY: NicheQueryInput = { city: "", service: "" };

// ---------------------------------------------------------------------------
// Mock CityAutocomplete.
//
// We capture the onChange callback each time the component renders so that
// tests can call it directly — both as a plain string (free-typed) and as
// a string+MetroSuggestion pair (dropdown selection).
// ---------------------------------------------------------------------------
let capturedOnChange: ((city: string, suggestion?: MetroSuggestion) => void) | null = null;

vi.mock("@/components/niche-finder/CityAutocomplete", () => ({
  default: ({
    value,
    onChange,
    disabled,
    "data-testid": testId,
  }: {
    value: string;
    onChange: (city: string, suggestion?: MetroSuggestion) => void;
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
describe("StandardNicheForm", () => {
  it("renders city-input, service-input, and submit button", () => {
    render(<StandardNicheForm initialQuery={INITIAL_QUERY} onSubmit={vi.fn()} />);
    expect(screen.getByTestId("city-input")).toBeInTheDocument();
    expect(screen.getByTestId("service-input")).toBeInTheDocument();
    expect(screen.getByTestId("score-niche-btn")).toBeInTheDocument();
  });

  it("selecting a suggestion populates both city and state on submit", () => {
    const onSubmit = vi.fn();
    render(<StandardNicheForm initialQuery={INITIAL_QUERY} onSubmit={onSubmit} />);

    // Simulate the user picking Phoenix from the dropdown
    act(() => {
      capturedOnChange!("Phoenix, AZ", PHOENIX_SUGGESTION);
    });

    fireEvent.change(screen.getByTestId("service-input"), {
      target: { value: "roofing" },
    });

    fireEvent.submit(screen.getByTestId("score-niche-btn").closest("form")!);

    expect(onSubmit).toHaveBeenCalledOnce();
    const submitted: NicheQueryInput = onSubmit.mock.calls[0][0];
    expect(submitted.city).toBe("Phoenix");
    expect(submitted.state).toBe("AZ");
    expect(submitted.service).toBe("roofing");
  });

  it("editing city after selecting a suggestion clears state", () => {
    const onSubmit = vi.fn();
    render(<StandardNicheForm initialQuery={INITIAL_QUERY} onSubmit={onSubmit} />);

    // First select a suggestion to populate state
    act(() => {
      capturedOnChange!("Phoenix, AZ", PHOENIX_SUGGESTION);
    });

    // Then free-type a different city — state should be cleared
    fireEvent.change(screen.getByTestId("city-input"), {
      target: { value: "Scottsdale" },
    });

    fireEvent.change(screen.getByTestId("service-input"), {
      target: { value: "roofing" },
    });

    fireEvent.submit(screen.getByTestId("score-niche-btn").closest("form")!);

    expect(onSubmit).toHaveBeenCalledOnce();
    const submitted: NicheQueryInput = onSubmit.mock.calls[0][0];
    expect(submitted.city).toBe("Scottsdale");
    expect(submitted.state).toBeUndefined();
  });

  it("submitting with only free-typed city sends state: undefined", () => {
    const onSubmit = vi.fn();
    render(<StandardNicheForm initialQuery={INITIAL_QUERY} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByTestId("city-input"), {
      target: { value: "Austin" },
    });
    fireEvent.change(screen.getByTestId("service-input"), {
      target: { value: "plumbing" },
    });

    fireEvent.submit(screen.getByTestId("score-niche-btn").closest("form")!);

    expect(onSubmit).toHaveBeenCalledOnce();
    const submitted: NicheQueryInput = onSubmit.mock.calls[0][0];
    expect(submitted.city).toBe("Austin");
    expect(submitted.service).toBe("plumbing");
    expect(submitted.state).toBeUndefined();
  });

  it("is disabled when disabled prop is true", () => {
    render(
      <StandardNicheForm
        initialQuery={INITIAL_QUERY}
        onSubmit={vi.fn()}
        disabled={true}
      />,
    );
    expect(screen.getByTestId("city-input")).toBeDisabled();
    expect(screen.getByTestId("service-input")).toBeDisabled();
    expect(screen.getByTestId("score-niche-btn")).toBeDisabled();
  });
});
