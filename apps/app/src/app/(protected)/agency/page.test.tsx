// @vitest-environment jsdom
import React from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import AgencyPage from "./page";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const originalFetch = global.fetch;

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  global.fetch = originalFetch;
});

describe("AgencyPage", () => {
  it("renders the multi-market batch flow and queues selected targets", async () => {
    const user = userEvent.setup();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            markets: [
              {
                rank: 1,
                opportunity_score: 84.2,
                city: {
                  city_id: "12420",
                  name: "Austin",
                  state: "TX",
                  population: 974000,
                },
                service: { service_id: "roofing", name: "Roofing" },
              },
            ],
          }),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            run_id: "run-1",
            status: "queued",
            target_count: 1,
          }),
          { status: 200 },
        ),
      );
    global.fetch = fetchMock;

    render(<AgencyPage />);

    expect(
      screen.getByRole("heading", { name: /Qualify territories in one batch/i }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Scans available")).toHaveTextContent(
      "1scan per queued batch",
    );

    await user.click(screen.getByRole("button", { name: /Roofing/i }));
    await user.click(screen.getByRole("button", { name: /Review targets/i }));

    expect(
      await screen.findByRole("heading", { name: "Confirm the batch" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Austin, TX")).toBeInTheDocument();
    expect(screen.getAllByText("Roofing").length).toBeGreaterThan(0);

    await user.click(screen.getByRole("button", { name: /Queue batch/i }));

    expect(await screen.findByRole("heading", { name: "Scan queued" })).toBeInTheDocument();
    expect(screen.getByText(/run-1/)).toBeInTheDocument();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/strategies/discover");
    const discoveryPayload = JSON.parse(fetchMock.mock.calls[0][1]?.body as string);
    expect(discoveryPayload).toMatchObject({
      lens_id: "easy_win",
      service_filters: [{ field: "name", operator: "like", value: "Roofing" }],
      limit: 25,
    });

    expect(fetchMock.mock.calls[1][0]).toBe("/api/strategies/runs");
    const runPayload = JSON.parse(fetchMock.mock.calls[1][1]?.body as string);
    expect(runPayload).toMatchObject({
      mode: "fresh",
      strategy_id: "easy_win",
      targets: [
        {
          cbsa_code: "12420",
          niche_normalized: "roofing",
          niche_keyword: "Roofing",
        },
      ],
    });
  });

  it("includes selected states in target discovery filters", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          markets: [
            {
              city: { city_id: "38060", name: "Phoenix", state: "AZ" },
              service: { service_id: "plumbing", name: "Plumbing" },
            },
          ],
        }),
        { status: 200 },
      ),
    );
    global.fetch = fetchMock;

    render(<AgencyPage />);

    await user.click(screen.getByRole("button", { name: "Select states" }));
    await user.click(screen.getByRole("option", { name: /AZ Arizona/i }));
    await user.click(screen.getByRole("button", { name: "Done" }));
    await user.click(screen.getByRole("button", { name: /Plumbing/i }));
    await user.click(screen.getByRole("button", { name: /Review targets/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const discoveryPayload = JSON.parse(fetchMock.mock.calls[0][1]?.body as string);
    expect(discoveryPayload.city_filters).toContainEqual({
      field: "state",
      operator: "in",
      value: ["AZ"],
    });
  });

  it("validates population filters before target discovery", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn();
    global.fetch = fetchMock;

    render(<AgencyPage />);

    const minInput = screen.getByLabelText("Minimum population");
    await user.clear(minInput);
    await user.type(minInput, "50,000");
    await user.click(screen.getByRole("button", { name: /Plumbing/i }));

    expect(screen.getByText("Population filters need whole numbers only.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Review targets/i })).toBeDisabled();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("blocks review until a service is selected", () => {
    render(<AgencyPage />);

    expect(screen.getByText("Select at least one service.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Review targets/i })).toBeDisabled();
  });
});
