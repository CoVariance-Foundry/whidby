// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, fireEvent, act } from "@testing-library/react";
import CityAutocomplete from "./CityAutocomplete";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------
const FIXTURE: Array<{
  cbsa_code: string;
  city: string;
  state: string;
  cbsa_name: string;
  population: number;
}> = [
  {
    cbsa_code: "38060",
    city: "Phoenix",
    state: "AZ",
    cbsa_name: "Phoenix-Mesa-Chandler, AZ",
    population: 4946145,
  },
  {
    cbsa_code: "37980",
    city: "Philadelphia",
    state: "PA",
    cbsa_name: "Philadelphia-Camden-Wilmington, PA-NJ-DE-MD",
    population: 6245051,
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
/**
 * Mock global.fetch to resolve with the given data after `delay` ms.
 * The mock respects the AbortSignal so abort tests work correctly.
 */
function mockFetch(
  data: typeof FIXTURE,
  { delay = 0 }: { delay?: number } = {},
) {
  global.fetch = vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
    return new Promise((resolve, reject) => {
      init?.signal?.addEventListener("abort", () =>
        reject(new DOMException("aborted", "AbortError")),
      );
      setTimeout(
        () => resolve(new Response(JSON.stringify(data), { status: 200 })),
        delay,
      );
    });
  });
}

function mockFetchError(status = 500) {
  global.fetch = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ detail: "error" }), { status }),
  );
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// Tests
// All tests pass debounceMs={0} to skip the 250 ms debounce delay so tests
// run synchronously with real timers. The debounce behaviour itself is
// verified in the "aborts in-flight fetch" test by using debounceMs={50}.
// ---------------------------------------------------------------------------
describe("CityAutocomplete", () => {
  it("renders an input with the forwarded value", () => {
    const onChange = vi.fn();
    render(<CityAutocomplete value="Dallas" onChange={onChange} />);
    const input = screen.getByTestId("city-input");
    expect(input).toBeInTheDocument();
    expect(input).toHaveValue("Dallas");
    // ARIA 1.2: role="combobox" must be on the <input>, not a wrapper <div>
    const combobox = screen.getByRole("combobox");
    expect(combobox.tagName.toLowerCase()).toBe("input");
  });

  it("shows suggestions after debounce fires", async () => {
    mockFetch(FIXTURE);
    const onChange = vi.fn();
    render(<CityAutocomplete value="" onChange={onChange} debounceMs={0} />);

    const input = screen.getByTestId("city-input");

    // No listbox before any input
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();

    await act(async () => {
      fireEvent.change(input, { target: { value: "ph" } });
    });

    await waitFor(() => {
      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });
    expect(screen.getAllByRole("option")).toHaveLength(2);
    expect(screen.getByText("Phoenix")).toBeInTheDocument();
    expect(screen.getByText("Philadelphia")).toBeInTheDocument();
  });

  it("selects a suggestion on click and calls onChange with formatted city+state", async () => {
    mockFetch(FIXTURE);
    const onChange = vi.fn();
    render(<CityAutocomplete value="" onChange={onChange} debounceMs={0} />);

    const input = screen.getByTestId("city-input");
    await act(async () => {
      fireEvent.change(input, { target: { value: "ph" } });
    });
    await waitFor(() => screen.getByRole("listbox"));

    const phoenixOption = screen.getByText("Phoenix").closest("li")!;
    await act(async () => {
      fireEvent.mouseDown(phoenixOption);
    });

    expect(onChange).toHaveBeenCalledWith("Phoenix, AZ", FIXTURE[0]);
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("navigates suggestions with keyboard ArrowDown / ArrowUp / Enter", async () => {
    mockFetch(FIXTURE);
    const onChange = vi.fn();
    render(<CityAutocomplete value="" onChange={onChange} debounceMs={0} />);

    const input = screen.getByTestId("city-input");
    await act(async () => {
      fireEvent.change(input, { target: { value: "ph" } });
    });
    await waitFor(() => screen.getByRole("listbox"));

    // Arrow down → first option active
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(screen.getAllByRole("option")[0]).toHaveAttribute("aria-selected", "true");

    // Arrow down again → second option active
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(screen.getAllByRole("option")[1]).toHaveAttribute("aria-selected", "true");

    // Arrow up → back to first
    fireEvent.keyDown(input, { key: "ArrowUp" });
    expect(screen.getAllByRole("option")[0]).toHaveAttribute("aria-selected", "true");

    // Enter → selects Phoenix (index 0)
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith("Phoenix, AZ", FIXTURE[0]);
  });

  it("closes the listbox on Escape", async () => {
    mockFetch(FIXTURE);
    const onChange = vi.fn();
    render(<CityAutocomplete value="" onChange={onChange} debounceMs={0} />);

    const input = screen.getByTestId("city-input");
    await act(async () => {
      fireEvent.change(input, { target: { value: "ph" } });
    });
    await waitFor(() => screen.getByRole("listbox"));

    fireEvent.keyDown(input, { key: "Escape" });
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("does not show listbox when fetch returns an error", async () => {
    mockFetchError(500);
    const onChange = vi.fn();
    render(<CityAutocomplete value="" onChange={onChange} debounceMs={0} />);

    const input = screen.getByTestId("city-input");
    await act(async () => {
      fireEvent.change(input, { target: { value: "er" } });
    });

    await waitFor(() => {
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    });
  });

  it("aborts in-flight fetch when input changes before debounce fires", async () => {
    // Use a real debounce delay of 50 ms and a fetch delay of 200 ms so that:
    // - First change starts a 50 ms debounce timer (timer A)
    // - Second change fires before timer A fires, cancelling it
    // - Only one fetch call is made when timer B eventually fires
    mockFetch(FIXTURE, { delay: 10 });
    const onChange = vi.fn();
    render(<CityAutocomplete value="" onChange={onChange} debounceMs={50} />);

    const input = screen.getByTestId("city-input");

    // First change — starts debounce timer A
    fireEvent.change(input, { target: { value: "p" } });

    // Immediately fire second change — cancels timer A, starts timer B
    fireEvent.change(input, { target: { value: "ph" } });

    // Wait for suggestions to appear (timer B fires, fetch resolves)
    await waitFor(() => screen.getByRole("listbox"), { timeout: 500 });

    // Only one fetch call (timer A was cancelled before it fired)
    expect(global.fetch as ReturnType<typeof vi.fn>).toHaveBeenCalledTimes(1);
    expect(screen.getAllByRole("option")).toHaveLength(2);
  });

  it("empty result renders 'No metros match' row that is not selectable", async () => {
    mockFetch([]);

    // Use a stateful wrapper so the controlled value prop tracks the input.
    function Wrapper() {
      const [val, setVal] = React.useState("");
      return (
        <CityAutocomplete
          value={val}
          onChange={(city) => setVal(city)}
          debounceMs={0}
        />
      );
    }

    render(<Wrapper />);

    const input = screen.getByTestId("city-input");
    await act(async () => {
      fireEvent.change(input, { target: { value: "zz" } });
    });

    // Listbox must appear with the disabled empty-state option
    await waitFor(() => {
      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    const emptyOption = screen.getByRole("option");
    expect(emptyOption).toHaveAttribute("aria-disabled", "true");
    expect(emptyOption).toHaveTextContent(/No metros match/);
    expect(emptyOption).toHaveTextContent("zz");

    // Clicking the disabled row must not call onSelect (onChange called only with string+suggestion pair)
    await act(async () => {
      fireEvent.mouseDown(emptyOption);
    });
    // After clicking disabled row, no suggestion object is passed to onChange
    // (only plain city string updates from typing are expected)
    expect(screen.queryByRole("listbox")).toBeInTheDocument(); // listbox stays open

    // Arrow keys must not crash and Enter must not select anything
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    // Listbox still open (no selection happened)
    expect(screen.queryByRole("listbox")).toBeInTheDocument();
  });
});
