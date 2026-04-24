import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MacroPage } from "../../../pages/macro-page";

const macroPayload = {
  generated_at: "2026-03-30T09:00:00Z",
  module: {
    id: "macro",
    label: "Macro Intelligence",
    note: "2 comparison cards",
    description: "Official macro comparisons with side-by-side indicators and source links.",
    status: "live",
    loading: false,
    details: [
      {
        id: "inflation-growth",
        label: "Inflation vs growth",
        kind: "macro",
        note: "Consumer prices remain sticky while growth stays resilient.",
        section: {
          key: "inflation-growth",
          title: "Inflation vs growth",
          status: "live",
          description: "A calm comparison of price pressure and activity.",
          summary: "CPI: 0.3% | GDP: 2.4%",
          primary: {
            key: "cpi",
            label: "CPI",
            status: "live",
            latest_value: "0.3%",
            previous_value: "0.2%",
            change_label: "+0.1 pts",
            trend: "up",
            frequency: "monthly",
            source_label: "National Bureau of Statistics",
            source_url: "https://example.com/cpi",
            updated_at: "2026-03-30T08:30:00Z",
            period_label: "Feb 2026",
            context: "Price growth stayed contained.",
            unit: "%",
            points: [
              { period_end: "2026-01-31", period_label: "Jan 2026", value: 0.2 },
              { period_end: "2026-02-28", period_label: "Feb 2026", value: 0.3 },
            ],
          },
          secondary: {
            key: "gdp",
            label: "GDP",
            status: "live",
            latest_value: "2.4%",
            previous_value: "2.2%",
            change_label: "+0.2 pts",
            trend: "up",
            frequency: "quarterly",
            source_label: "National Bureau of Statistics",
            source_url: "https://example.com/gdp",
            updated_at: "2026-03-30T08:30:00Z",
            period_label: "Q4 2025",
            context: "Activity held up into year end.",
            unit: "%",
            points: [
              { period_end: "2025-09-30", period_label: "Q3 2025", value: 2.2 },
              { period_end: "2025-12-31", period_label: "Q4 2025", value: 2.4 },
            ],
          },
          delta_label: "Gap",
          delta_points: [
            { period_end: "2026-02-28", period_label: "Feb 2026", value: -2.1 },
          ],
          sources: [
            { label: "National Bureau of Statistics", url: "https://example.com/cpi" },
            { label: "National Bureau of Statistics", url: "https://example.com/gdp" },
          ],
        },
      },
      {
        id: "rates-liquidity",
        label: "Rates vs liquidity",
        kind: "macro",
        note: "Policy rates and lending conditions are stabilizing.",
        section: {
          key: "rates-liquidity",
          title: "Rates vs liquidity",
          status: "sample",
          description: "Policy stance and money conditions side by side.",
          summary: "Rates: 3.5% | Liquidity: 6.2%",
          primary: {
            key: "policy-rates",
            label: "Policy rates",
            status: "live",
            latest_value: "3.5%",
            previous_value: "3.6%",
            change_label: "-0.1 pts",
            trend: "down",
            frequency: "monthly",
            source_label: "Central Bank",
            source_url: "https://example.com/rates",
            updated_at: "2026-03-30T08:30:00Z",
            period_label: "Mar 2026",
            context: "Rates remained steady.",
            unit: "%",
            points: [],
          },
          secondary: null,
          delta_label: "Spread",
          delta_points: [],
          sources: [{ label: "Central Bank", url: "https://example.com/rates" }],
        },
      },
    ],
  },
};

describe("MacroPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  function renderMacroPage(initialEntry = "/macro?tab=compare") {
    const router = createMemoryRouter(
      [
        {
          path: "/macro",
          element: <MacroPage />,
        },
      ],
      {
        initialEntries: [initialEntry],
      },
    );

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );
  }

  it("renders comparison cards, summary text, and sources from the module payload", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(macroPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    renderMacroPage("/macro?tab=compare");

    expect(await screen.findByRole("heading", { name: "Inflation vs growth" })).toBeInTheDocument();
    expect(screen.getByText("CPI: 0.3% | GDP: 2.4%")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Inflation vs growth relative performance chart" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Inflation vs growth spread chart" })).toBeInTheDocument();
    expect(screen.getAllByText("Pair correlation").length).toBeGreaterThan(0);
    expect(screen.getAllByText("National Bureau of Statistics").length).toBeGreaterThan(0);
    const statsHrefs = screen
      .getAllByRole("link", { name: "National Bureau of Statistics" })
      .map((link) => link.getAttribute("href"));
    expect(statsHrefs).toContain("https://example.com/cpi");
    expect(statsHrefs).toContain("https://example.com/gdp");
  });

  it("renders time-series charts inside the indicators tab", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(macroPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    renderMacroPage("/macro?tab=indicators");

    expect(await screen.findByRole("heading", { name: "Pair raw series" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Inflation vs growth primary series chart" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Inflation vs growth secondary series chart" })).toBeInTheDocument();
    expect(screen.getAllByText("Primary series").length).toBeGreaterThan(0);
  });

  it("falls back to overview when the tab query is unknown", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(macroPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    renderMacroPage("/macro?tab=nope");

    expect(await screen.findByRole("heading", { name: "Macro pair monitor" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");
  });

  it("renders the loading state inside the shared module frame", () => {
    vi.spyOn(globalThis, "fetch").mockImplementationOnce(() => new Promise(() => {}));

    renderMacroPage("/macro?tab=compare");

    expect(screen.getByRole("heading", { name: "Macro" })).toBeInTheDocument();
    expect(screen.getByText("Loading macro comparisons")).toBeInTheDocument();
    expect(screen.getByText("Source panel loading")).toBeInTheDocument();
  });

  it("renders the error state inside the shared module frame", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("network down"));

    renderMacroPage("/macro?tab=compare");

    expect(await screen.findByText("Macro module unavailable")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Macro" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("renders the empty state inside the shared module frame", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          ...macroPayload,
          module: {
            ...macroPayload.module,
            details: [],
            note: "0 comparison cards",
          },
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    renderMacroPage("/macro?tab=overview");

    expect(await screen.findByText("No macro comparisons yet")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Macro" })).toBeInTheDocument();
    expect(screen.getByText("Official macro comparisons with side-by-side indicators and source links.")).toBeInTheDocument();
  });
});
