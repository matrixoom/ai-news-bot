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

  it("renders comparison cards, summary text, and sources from the module payload", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(macroPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const router = createMemoryRouter(
      [
        {
          path: "/macro",
          element: <MacroPage />,
        },
      ],
      {
        initialEntries: ["/macro?tab=compare"],
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

    expect(await screen.findByRole("heading", { name: "Inflation vs growth" })).toBeInTheDocument();
    expect(screen.getByText("CPI: 0.3% | GDP: 2.4%")).toBeInTheDocument();
    expect(screen.getAllByText("National Bureau of Statistics").length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "National Bureau of Statistics" })[0]).toHaveAttribute(
      "href",
      "https://example.com/cpi",
    );
  });

  it("falls back to overview when the tab query is unknown", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(macroPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const router = createMemoryRouter(
      [
        {
          path: "/macro",
          element: <MacroPage />,
        },
      ],
      {
        initialEntries: ["/macro?tab=nope"],
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

    expect(await screen.findByRole("heading", { name: "Macro overview" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");
  });
});
