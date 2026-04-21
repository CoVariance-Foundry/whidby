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
// Tests — mirrors admin CityAutocomplete.test.tsx; light theme, same behavior
// ---------------------------------------------------------------------------
describe("CityAutocomplete (consumer)", () => {
  it("renders an input with the forwarded value", () => {
    const onChange = vi.fn();
    render(<CityAutocomplete value="Dallas" onChange={onChange} />);
    const input = screen.getByTestId("city-input");
    expect(input).toBeInTheDocument();
    expect(input).toHaveValue("Dallas");
    const combobox = screen.getByRole("combobox");
    expect(combobox.tagName.toLowerCase()).toBe("input");
  });

  it("shows suggestions after debounce fires", async () => {
    mockFetch(FIXTURE);
    const onChange = vi.fn();
    render(<CityAutocomplete value="" onChange={onChange} debounceMs={0} />);

    const input = screen.getByTestId("city-input");
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

    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(screen.getAllByRole("option")[0]).toHaveAttribute("aria-selected", "true");

    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(screen.getAllByRole("option")[1]).toHaveAttribute("aria-selected", "true");

    fireEvent.keyDown(input, { key: "ArrowUp" });
    expect(screen.getAllByRole("option")[0]).toHaveAttribute("aria-selected", "true");

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

  it("empty result renders 'No metros match' row that is not selectable", async () => {
    mockFetch([]);

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

    await waitFor(() => {
      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    const emptyOption = screen.getByRole("option");
    expect(emptyOption).toHaveAttribute("aria-disabled", "true");
    expect(emptyOption).toHaveTextContent(/No metros match/);
    expect(emptyOption).toHaveTextContent("zz");

    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(screen.queryByRole("listbox")).toBeInTheDocument();
  });
});
