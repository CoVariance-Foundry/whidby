// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { StrategyCatalogEntry } from "@/lib/strategies/types";
import StrategyPageClient from "./StrategyPageClient";

const originalFetch = global.fetch;

afterEach(() => {
  cleanup();
  global.fetch = originalFetch;
  vi.restoreAllMocks();
});

describe("StrategyPageClient", () => {
  it("keeps the keyword_hijack payload shape and renders the hero results layout", async () => {
    const strategy: StrategyCatalogEntry = {
      strategy_id: "keyword_hijack",
      name: "Keyword Hijack",
      description: "Keyword-led markets.",
      status: "launch",
      input_shape: "city_service_keyword",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          markets: [
            {
              rank: 1,
              opportunity_score: 86,
              city: { city_id: "boise-id", name: "Boise", state: "ID" },
              service: { service_id: "plumbing", name: "Plumbing" },
              score_breakdown: {
                search_volume_monthly: 720,
                organic_competition: 48,
                ai_resilience: 82,
                confidence: { score: 91 },
              },
              strategy_evidence: {
                local_pack_present: true,
              },
              warnings: ["AI overview present"],
            },
          ],
        }),
        { status: 200 },
      ),
    );
    global.fetch = fetchMock;

    render(<StrategyPageClient strategy={strategy} />);

    fireEvent.change(screen.getByLabelText("City"), { target: { value: "Boise" } });
    fireEvent.change(screen.getByLabelText("Service"), { target: { value: "plumbing" } });
    fireEvent.change(screen.getByLabelText("Primary keyword"), {
      target: { value: "boise plumber" },
    });
    fireEvent.click(screen.getByRole("button", { name: /run discovery/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/strategies/discover");
    expect(body).toMatchObject({
      lens_id: "keyword_hijack",
      primary_keyword: "boise plumber",
      ai_resilience_filter: false,
      limit: 10,
    });
    expect(body.city_filters).toEqual([{ field: "name", operator: "like", value: "Boise" }]);
    expect(body.service_filters).toEqual([{ field: "name", operator: "like", value: "plumbing" }]);

    expect(await screen.findByText("Keyword Hijack results")).toBeInTheDocument();
    expect(screen.getByText("Plumbing in Boise")).toBeInTheDocument();
    expect(screen.getByText("Composite opportunity score")).toBeInTheDocument();
    expect(screen.getByText("Time-to-rank: Moderate")).toBeInTheDocument();
    expect(screen.getByText("Search Volume Monthly")).toBeInTheDocument();
    expect(screen.getByText("Organic Competition")).toBeInTheDocument();
    expect(screen.getByText("Local Pack Present")).toBeInTheDocument();
    expect(screen.getByText("AI resilience: 82")).toBeInTheDocument();
    expect(screen.getAllByLabelText("Signal trend up").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Signal trend down")).toBeInTheDocument();
    expect(screen.getByLabelText("Result warnings")).toHaveTextContent("AI overview present");
    expect(screen.getByLabelText("Strategy score")).toHaveTextContent("86");
  });

  it("sends reference_city_id for Expand & Conquer", async () => {
    const strategy: StrategyCatalogEntry = {
      strategy_id: "expand_conquer",
      name: "Expand & Conquer",
      description: "Reference-market expansion.",
      status: "launch",
      input_shape: "reference_city_service",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ markets: [] }), { status: 200 }),
    );
    global.fetch = fetchMock;

    render(<StrategyPageClient strategy={strategy} />);

    fireEvent.change(screen.getByLabelText("Reference city id"), {
      target: { value: "boise-id" },
    });
    fireEvent.change(screen.getByLabelText("Service"), { target: { value: "plumbing" } });
    fireEvent.click(screen.getByRole("button", { name: /run discovery/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(body).toMatchObject({
      lens_id: "expand_conquer",
      reference_city_id: "boise-id",
    });
    expect(body.service_filters).toEqual([{ field: "name", operator: "like", value: "plumbing" }]);
  });

  it("adds encoded Next Moves links from the top result context", async () => {
    const strategy: StrategyCatalogEntry = {
      strategy_id: "easy_win",
      name: "Easy Win",
      description: "Cached market discovery.",
      status: "launch",
      input_shape: "city_service",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          results: [
            {
              rank: 1,
              score: 78,
              city_name: "New York",
              service_name: "garage door repair",
              score_breakdown: { demand: 77 },
            },
          ],
        }),
        { status: 200 },
      ),
    );
    global.fetch = fetchMock;

    render(<StrategyPageClient strategy={strategy} />);

    fireEvent.change(screen.getByLabelText("City"), { target: { value: "New York" } });
    fireEvent.change(screen.getByLabelText("Service"), { target: { value: "garage door repair" } });
    fireEvent.click(screen.getByRole("button", { name: /run discovery/i }));

    const reportLibrary = await screen.findByRole("link", { name: /review report library/i });
    expect(reportLibrary).toHaveAttribute("href", "/reports");
    expect(screen.getByRole("link", { name: /browse similar markets/i })).toHaveAttribute(
      "href",
      "/explore?city=New%20York&service=garage%20door%20repair",
    );
  });

  it("renders the Blue Ocean two-card Next Moves set", async () => {
    const strategy: StrategyCatalogEntry = {
      strategy_id: "blue_ocean",
      name: "Blue Ocean",
      description: "Find under-contested markets.",
      status: "launch",
      input_shape: "city_service",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          markets: [
            {
              rank: 1,
              score: 88,
              city_name: "Denver",
              service_name: "roof repair",
            },
          ],
        }),
        { status: 200 },
      ),
    );
    global.fetch = fetchMock;

    render(<StrategyPageClient strategy={strategy} />);

    fireEvent.change(screen.getByLabelText("City"), { target: { value: "Denver" } });
    fireEvent.change(screen.getByLabelText("Service"), { target: { value: "roof repair" } });
    fireEvent.click(screen.getByRole("button", { name: /run discovery/i }));

    expect(await screen.findByRole("link", { name: /validate rank ease/i })).toHaveAttribute(
      "href",
      "/strategies/easy_win",
    );
    expect(screen.getByRole("link", { name: /check cities for #1/i })).toHaveAttribute(
      "href",
      "/explore",
    );
    expect(screen.getByText("Check whether roof repair in Denver can rank quickly.")).toBeInTheDocument();
    expect(screen.getAllByRole("link")).toHaveLength(2);
  });

  it("does not submit phase_2 strategies", () => {
    const strategy: StrategyCatalogEntry = {
      strategy_id: "cash_cow",
      name: "Cash Cow",
      description: "Phase-2 scan.",
      status: "phase_2",
      input_shape: "cached_scan",
    };
    const fetchMock = vi.fn();
    global.fetch = fetchMock;

    render(<StrategyPageClient strategy={strategy} />);

    expect(screen.getByRole("status")).toHaveTextContent("phase-2 strategy");
    const submit = screen.getByRole("button", { name: /run discovery/i });
    expect(submit).toBeDisabled();
    fireEvent.click(submit);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
