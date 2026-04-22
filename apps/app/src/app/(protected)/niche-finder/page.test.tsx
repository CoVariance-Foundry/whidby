// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, fireEvent, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import NicheFinderClient from "./NicheFinderClient";

// ---------------------------------------------------------------------------
// Mock Next.js modules that don't work in jsdom
// ---------------------------------------------------------------------------
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: React.ReactNode; [k: string]: unknown }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/components/niche-finder/CityAutocomplete", () => ({
  default: ({
    value,
    onChange,
    disabled,
    "data-testid": testId = "city-input",
  }: {
    value: string;
    onChange: (city: string, suggestion?: { city: string; state: string }) => void;
    disabled?: boolean;
    "data-testid"?: string;
  }) => (
    <>
      <input
        data-testid={testId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        role="combobox"
        aria-expanded={false}
      />
      <button
        type="button"
        data-testid="city-select-phoenix-az"
        disabled={disabled}
        onClick={() =>
          onChange("Phoenix, AZ", {
            city: "Phoenix",
            state: "AZ",
          })
        }
      >
        Select Phoenix AZ
      </button>
    </>
  ),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

function renderClient() {
  return render(<NicheFinderClient />, { wrapper: createWrapper() });
}

function fillAndSubmit(city: string, service: string) {
  const cityInput = screen.getByTestId("city-input");
  const serviceInput = screen.getByTestId("service-input");
  const submitBtn = screen.getByTestId("submit-btn");

  fireEvent.change(cityInput, { target: { value: city } });
  fireEvent.change(serviceInput, { target: { value: service } });
  fireEvent.click(submitBtn);
}

const SUCCESS_RESPONSE = {
  status: "success",
  query: { city: "Phoenix", service: "roofing", state: "AZ" },
  score_result: { opportunity_score: 72, classification_label: "Medium" },
  report_id: "rpt-123",
  message: undefined,
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe("NicheFinderClient", () => {
  it("renders without crashing — heading and form are present", () => {
    renderClient();
    expect(screen.getByText("Find a niche")).toBeInTheDocument();
    expect(screen.getByTestId("city-input")).toBeInTheDocument();
    expect(screen.getByTestId("service-input")).toBeInTheDocument();
    expect(screen.getByTestId("submit-btn")).toBeInTheDocument();
  });

  it("shows a validation error when submitted with empty fields", async () => {
    renderClient();
    fireEvent.click(screen.getByTestId("submit-btn"));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
    expect(screen.getByRole("alert")).toHaveTextContent(/required/i);
  });

  it("submitting with city + service POSTs to /api/agent/scoring", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(SUCCESS_RESPONSE), { status: 200 }),
    );
    global.fetch = fetchMock;

    renderClient();
    await act(async () => {
      fillAndSubmit("Phoenix", "roofing");
    });

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/agent/scoring",
        expect.objectContaining({ method: "POST" }),
      );
    });

    const body = JSON.parse((fetchMock.mock.calls[0][1] as RequestInit).body as string);
    expect(body.city).toBe("Phoenix");
    expect(body.service).toBe("roofing");
  });

  it("success response renders the opportunity score", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(SUCCESS_RESPONSE), { status: 200 }),
    );

    renderClient();
    await act(async () => {
      fillAndSubmit("Phoenix", "roofing");
    });

    await waitFor(() => {
      expect(screen.getByTestId("opportunity-score")).toBeInTheDocument();
    });
    expect(screen.getByTestId("opportunity-score")).toHaveTextContent("72");
  });

  it("selected autocomplete suggestion sends canonical city + state", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(SUCCESS_RESPONSE), { status: 200 }),
    );
    global.fetch = fetchMock;

    renderClient();
    fireEvent.click(screen.getByTestId("city-select-phoenix-az"));
    fireEvent.change(screen.getByTestId("service-input"), {
      target: { value: "roofing" },
    });
    fireEvent.click(screen.getByTestId("submit-btn"));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    const body = JSON.parse((fetchMock.mock.calls[0][1] as RequestInit).body as string);
    expect(body.city).toBe("Phoenix");
    expect(body.state).toBe("AZ");
    expect(body.city).not.toBe("Phoenix, AZ");
  });

  it("success response renders a View full report link", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(SUCCESS_RESPONSE), { status: 200 }),
    );

    renderClient();
    await act(async () => {
      fillAndSubmit("Phoenix", "roofing");
    });

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /view full report/i })).toBeInTheDocument();
    });
    const link = screen.getByRole("link", { name: /view full report/i }) as HTMLAnchorElement;
    expect(link.href).toContain("/reports");
  });

  it("error response renders an alert banner", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ status: "unavailable", message: "Pipeline down." }),
        { status: 503 },
      ),
    );

    renderClient();
    await act(async () => {
      fillAndSubmit("Phoenix", "roofing");
    });

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
    expect(screen.getByRole("alert")).toHaveTextContent("Pipeline down.");
  });
});
