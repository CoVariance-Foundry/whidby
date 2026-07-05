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

  it("queues custom targets without selecting cached services", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          run_id: "run-custom",
          status: "queued",
          target_count: 1,
        }),
        { status: 200 },
      ),
    );
    global.fetch = fetchMock;

    render(<AgencyPage />);

    await user.click(screen.getByRole("button", { name: "Add custom target" }));
    await user.type(screen.getByLabelText("Custom target 1 city"), "Tulsa");
    await user.type(screen.getByLabelText("Custom target 1 state"), "OK");
    await user.type(screen.getByLabelText("Custom target 1 service"), "Water damage");
    await user.type(screen.getByLabelText("Custom target 1 primary keyword"), "water mitigation");
    await user.click(screen.getByRole("button", { name: /Review targets/i }));

    expect(
      await screen.findByRole("heading", { name: "Confirm the batch" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Tulsa, OK")).toBeInTheDocument();
    expect(screen.getByLabelText("Source custom/live")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Queue batch/i }));

    expect(await screen.findByRole("heading", { name: "Scan queued" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/strategies/runs");
    const runPayload = JSON.parse(fetchMock.mock.calls[0][1]?.body as string);
    expect(runPayload).toMatchObject({
      mode: "fresh",
      strategy_id: "easy_win",
      targets: [
        {
          cbsa_code: "custom:tulsa:ok",
          niche_normalized: "water_damage",
          niche_keyword: "Water damage",
          primary_keyword: "water mitigation",
        },
      ],
    });
  });

  it("requires a valid 2-letter state for custom targets before review", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn();
    global.fetch = fetchMock;

    render(<AgencyPage />);

    await user.click(screen.getByRole("button", { name: "Add custom target" }));
    await user.type(screen.getByLabelText("Custom target 1 city"), "Tulsa");
    await user.type(screen.getByLabelText("Custom target 1 service"), "Water damage");

    expect(
      screen.getByText("Custom targets need a city, 2-letter state, and valid service."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Review targets/i })).toBeDisabled();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("requires a backend-valid normalized service key for custom targets before review", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn();
    global.fetch = fetchMock;

    render(<AgencyPage />);

    await user.click(screen.getByRole("button", { name: "Add custom target" }));
    await user.type(screen.getByLabelText("Custom target 1 city"), "Tulsa");
    await user.type(screen.getByLabelText("Custom target 1 state"), "OK");
    await user.type(screen.getByLabelText("Custom target 1 service"), "!!");

    expect(
      screen.getByText("Custom targets need a city, 2-letter state, and valid service."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Review targets/i })).toBeDisabled();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("lets Keyword Hijack custom-only targets proceed with row-level primary keywords", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          run_id: "run-keyword",
          status: "queued",
          target_count: 1,
        }),
        { status: 200 },
      ),
    );
    global.fetch = fetchMock;

    render(<AgencyPage />);

    await user.click(screen.getByRole("button", { name: /Keyword Hijack/i }));
    await user.click(screen.getByRole("button", { name: "Add custom target" }));
    await user.type(screen.getByLabelText("Custom target 1 city"), "Tulsa");
    await user.type(screen.getByLabelText("Custom target 1 state"), "OK");
    await user.type(screen.getByLabelText("Custom target 1 service"), "Water damage");

    expect(
      screen.getByText(
        "Keyword Hijack needs a primary keyword on every custom target or in the global field.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Review targets/i })).toBeDisabled();
    expect(fetchMock).not.toHaveBeenCalled();

    const primaryKeywordInput = screen.getByLabelText("Custom target 1 primary keyword");
    await user.type(primaryKeywordInput, "plumber");
    expect(
      screen.getByText(
        "Keyword Hijack needs a primary keyword on every custom target or in the global field.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Review targets/i })).toBeDisabled();

    await user.clear(primaryKeywordInput);
    await user.type(primaryKeywordInput, "water mitigation");
    await user.click(screen.getByRole("button", { name: /Review targets/i }));

    expect(
      await screen.findByRole("heading", { name: "Confirm the batch" }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Queue batch/i }));

    expect(await screen.findByRole("heading", { name: "Scan queued" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const runPayload = JSON.parse(fetchMock.mock.calls[0][1]?.body as string);
    expect(runPayload).toMatchObject({
      mode: "fresh",
      strategy_id: "keyword_hijack",
      feasibility_preflight_passed: true,
      targets: [
        {
          cbsa_code: "custom:tulsa:ok",
          niche_normalized: "water_damage",
          niche_keyword: "Water damage",
          primary_keyword: "water mitigation",
        },
      ],
    });
    expect(runPayload.primary_keyword).toBeUndefined();
  });

  it("requires a global Keyword Hijack keyword for mixed cached and custom batches", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn();
    global.fetch = fetchMock;

    render(<AgencyPage />);

    await user.click(screen.getByRole("button", { name: /Keyword Hijack/i }));
    await user.click(screen.getByRole("button", { name: /Roofing/i }));
    await user.click(screen.getByRole("button", { name: "Add custom target" }));
    await user.type(screen.getByLabelText("Custom target 1 city"), "Boise");
    await user.type(screen.getByLabelText("Custom target 1 state"), "ID");
    await user.type(screen.getByLabelText("Custom target 1 service"), "Roof repair");
    await user.type(screen.getByLabelText("Custom target 1 primary keyword"), "roof repair");

    expect(
      screen.getByText("Keyword Hijack needs a global primary keyword for cached discovery."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Review targets/i })).toBeDisabled();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("reviews and queues cached and custom targets together with source labels", async () => {
    const user = userEvent.setup();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            markets: [
              {
                rank: 1,
                opportunity_score: 82,
                city: { city_id: "12420", name: "Austin", state: "TX" },
                service: { service_id: "roofing", name: "Roofing" },
              },
            ],
          }),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ run_id: "run-mixed", status: "queued", target_count: 2 }),
          { status: 200 },
        ),
      );
    global.fetch = fetchMock;

    render(<AgencyPage />);

    await user.click(screen.getByRole("button", { name: /Roofing/i }));
    await user.click(screen.getByRole("button", { name: "Add custom target" }));
    await user.type(screen.getByLabelText("Custom target 1 city"), "Boise");
    await user.type(screen.getByLabelText("Custom target 1 state"), "ID");
    await user.type(screen.getByLabelText("Custom target 1 service"), "Roof repair");
    await user.click(screen.getByRole("button", { name: /Review targets/i }));

    expect(
      await screen.findByRole("heading", { name: "Confirm the batch" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Austin, TX")).toBeInTheDocument();
    expect(screen.getByText("Boise, ID")).toBeInTheDocument();
    expect(screen.getByLabelText("Source cached")).toBeInTheDocument();
    expect(screen.getByLabelText("Source custom/live")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Queue batch/i }));

    const runPayload = JSON.parse(fetchMock.mock.calls[1][1]?.body as string);
    expect(runPayload.targets).toEqual([
      {
        cbsa_code: "12420",
        niche_normalized: "roofing",
        niche_keyword: "Roofing",
      },
      {
        cbsa_code: "custom:boise:id",
        niche_normalized: "roof_repair",
        niche_keyword: "Roof repair",
      },
    ]);
  });

  it("shows cached discovery zero-result recovery instead of a generic wall", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ markets: [] }), { status: 200 }),
    );
    global.fetch = fetchMock;

    render(<AgencyPage />);

    await user.click(screen.getByRole("button", { name: /Plumbing/i }));
    await user.click(screen.getByRole("button", { name: /Review targets/i }));

    expect(
      await screen.findByText("No cached markets matched this configuration."),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Add custom city-service targets to queue live research/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Add city-service targets/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Confirm the batch" }),
    ).not.toBeInTheDocument();
  });

  it("renders upgrade-path copy and settings link for tier-limit queue responses", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          status: "tier_limit",
          code: "fresh_strategy_runs_not_included",
        }),
        { status: 402 },
      ),
    );
    global.fetch = fetchMock;

    render(<AgencyPage />);

    await user.click(screen.getByRole("button", { name: "Add custom target" }));
    await user.type(screen.getByLabelText("Custom target 1 city"), "Savannah");
    await user.type(screen.getByLabelText("Custom target 1 state"), "GA");
    await user.type(screen.getByLabelText("Custom target 1 service"), "Pest control");
    await user.click(screen.getByRole("button", { name: /Review targets/i }));
    await user.click(await screen.findByRole("button", { name: /Queue batch/i }));

    expect(
      await screen.findByText("Fresh multi-market scans are an upgrade path."),
    ).toBeInTheDocument();
    expect(screen.getByText(/live batch runs require Plus or Pro/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open settings/i })).toHaveAttribute(
      "href",
      "/settings",
    );
  });

  it("renders quota-specific copy and settings link for quota exhaustion responses", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          status: "quota_exceeded",
          code: "monthly_report_quota_exceeded",
        }),
        { status: 402 },
      ),
    );
    global.fetch = fetchMock;

    render(<AgencyPage />);

    await user.click(screen.getByRole("button", { name: "Add custom target" }));
    await user.type(screen.getByLabelText("Custom target 1 city"), "Madison");
    await user.type(screen.getByLabelText("Custom target 1 state"), "WI");
    await user.type(screen.getByLabelText("Custom target 1 service"), "HVAC");
    await user.click(screen.getByRole("button", { name: /Review targets/i }));
    await user.click(await screen.findByRole("button", { name: /Queue batch/i }));

    expect(await screen.findByText("Monthly report quota reached.")).toBeInTheDocument();
    expect(screen.getByText(/needs one report credit/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open settings/i })).toHaveAttribute(
      "href",
      "/settings",
    );
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

  it("ignores stale cached discovery responses after inputs change during preparation", async () => {
    const user = userEvent.setup();
    let resolveDiscover: (response: Response) => void = () => {};
    const discoveryPromise = new Promise<Response>((resolve) => {
      resolveDiscover = resolve;
    });
    const fetchMock = vi.fn().mockReturnValueOnce(discoveryPromise);
    global.fetch = fetchMock;

    render(<AgencyPage />);

    await user.click(screen.getByRole("button", { name: /Plumbing/i }));
    await user.click(screen.getByRole("button", { name: /Review targets/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    await user.click(screen.getByRole("button", { name: /Roofing/i }));
    resolveDiscover(
      new Response(
        JSON.stringify({
          markets: [
            {
              city: { city_id: "12420", name: "Austin", state: "TX" },
              service: { service_id: "plumbing", name: "Plumbing" },
            },
          ],
        }),
        { status: 200 },
      ),
    );

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /Review targets/i })).toBeEnabled(),
    );
    expect(screen.queryByRole("heading", { name: "Confirm the batch" })).not.toBeInTheDocument();
    expect(screen.queryByText("Austin, TX")).not.toBeInTheDocument();
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

    expect(
      screen.getByText("Select cached services or add a custom city-service target."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Review targets/i })).toBeDisabled();
  });
});
