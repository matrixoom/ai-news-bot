import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MarketPage } from "../../../pages/market-page";

const marketPayload = {
  generated_at: "2026-03-30T09:00:00Z",
  module: {
    id: "market",
    label: "Market Models",
    note: "3 model cards",
    description: "Signal-first market models with a calm watch panel.",
    status: "live",
    loading: false,
    details: [
      {
        id: "csi-300",
        label: "CSI 300",
        kind: "market",
        note: "neutral",
        section: {
          key: "csi-300",
          label: "CSI 300",
          status: "live",
          close_value: "3,864.2",
          ma20_value: "3,850.1",
          signal: "neutral",
          deviation_pct: 0.4,
          trade_date: "2026-03-29",
          source_label: "SSE",
          explanation: "Benchmarks held near trend support.",
          data_window_label: "20 sessions",
          history_warning: "",
          chart_points: [
            { trade_date: "2026-03-27", close_price: 3857.4, ma20_price: 3847.8, deviation_pct: 0.2 },
            { trade_date: "2026-03-28", close_price: 3861.1, ma20_price: 3849.2, deviation_pct: 0.3 },
            { trade_date: "2026-03-29", close_price: 3864.2, ma20_price: 3850.1, deviation_pct: 0.4 },
          ],
        },
      },
      {
        id: "hstech",
        label: "HSTECH",
        kind: "market",
        note: "constructive",
        section: {
          key: "hstech",
          label: "HSTECH",
          status: "sample",
          close_value: "3,092.5",
          ma20_value: "3,071.4",
          signal: "constructive",
          deviation_pct: 0.7,
          trade_date: "2026-03-29",
          source_label: "HKEX",
          explanation: "Tech leadership improved into the close.",
          data_window_label: "20 sessions",
          history_warning: "History still thin for this series.",
          chart_points: [
            { trade_date: "2026-03-27", close_price: 3079.8, ma20_price: 3065.9, deviation_pct: 0.5 },
            { trade_date: "2026-03-28", close_price: 3088.4, ma20_price: 3068.6, deviation_pct: 0.6 },
            { trade_date: "2026-03-29", close_price: 3092.5, ma20_price: 3071.4, deviation_pct: 0.7 },
          ],
        },
      },
      {
        id: "sse-composite",
        label: "SSE Composite",
        kind: "market",
        note: "pressured",
        section: {
          key: "sse-composite",
          label: "SSE Composite",
          status: "live",
          close_value: "3,215.8",
          ma20_value: "3,228.0",
          signal: "pressured",
          deviation_pct: -0.4,
          trade_date: "2026-03-29",
          source_label: "SSE",
          explanation: "Breadth remained soft beneath the index.",
          data_window_label: "20 sessions",
          history_warning: "",
          chart_points: [
            { trade_date: "2026-03-27", close_price: 3221.0, ma20_price: 3226.6, deviation_pct: -0.2 },
            { trade_date: "2026-03-28", close_price: 3218.2, ma20_price: 3227.2, deviation_pct: -0.3 },
            { trade_date: "2026-03-29", close_price: 3215.8, ma20_price: 3228.0, deviation_pct: -0.4 },
          ],
        },
      },
    ],
  },
};

describe("MarketPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  function renderMarketPage(initialEntry = "/market?tab=signals") {
    const router = createMemoryRouter(
      [
        {
          path: "/market",
          element: <MarketPage />,
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

  it("renders signal cards and watch summaries from the market payload", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(marketPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    renderMarketPage("/market?tab=signals");

    expect(await screen.findByRole("heading", { name: "CSI 300" })).toBeInTheDocument();
    expect(screen.getAllByText("neutral").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Watchlist" })).toBeInTheDocument();
    expect(screen.getByText("3 tracked signals")).toBeInTheDocument();
  });

  it("falls back to overview when the tab query is unknown", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(marketPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    renderMarketPage("/market?tab=nope");

    expect(await screen.findByRole("heading", { name: "Market overview" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");
  });

  it("accepts string deviation labels from the backend contract", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          ...marketPayload,
          module: {
            ...marketPayload.module,
            details: [
              {
                ...marketPayload.module.details[0],
                section: {
                  ...marketPayload.module.details[0].section,
                  deviation_pct: "+1.2%",
                },
              },
              {
                ...marketPayload.module.details[1],
                section: {
                  ...marketPayload.module.details[1].section,
                  deviation_pct: "暂无数据",
                },
              },
              marketPayload.module.details[2],
            ],
          },
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    renderMarketPage("/market?tab=signals");

    expect(await screen.findByText("+1.2%")).toBeInTheDocument();
    expect(screen.getByText("暂无数据")).toBeInTheDocument();
    expect(screen.getByText("+0.4%")).toBeInTheDocument();
  });
});
