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
  it("sends primary_keyword for keyword_hijack and renders a returned result", async () => {
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
              strategy_evidence: {
                search_volume_monthly: 720,
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

    expect(await screen.findByText("Plumbing in Boise")).toBeInTheDocument();
    expect(screen.getByText("search_volume_monthly: 720")).toBeInTheDocument();
    expect(screen.getByText("local_pack_present: yes")).toBeInTheDocument();
    const score = screen.getByRole("img", { name: "Strategy score: 86 out of 100, high" });
    expect(score).toHaveAttribute("data-score-tone", "high");
    expect(score).toHaveTextContent("86");
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
});
