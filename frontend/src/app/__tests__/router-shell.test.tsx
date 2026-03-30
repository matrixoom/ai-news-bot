import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../app";

const dashboardPayload = {
  generated_at: "2026-03-30T09:00:00Z",
  news_mode: "hybrid",
  news_mode_options: [{ value: "hybrid", label: "Hybrid" }],
  upstream_service_status: { status: "available", healthy: true, detail: "healthy" },
  title: "Trend Insights",
  subtitle: "Technology headlines turned constructive overnight.",
  coverage_note: "128 stories indexed in the last 24 hours.",
  highlights: ["Technology headlines turned constructive overnight."],
  news_sections: [
    {
      key: "top-news",
      title: "Top News",
      status: "live",
      description: "Leading developments across the news desk.",
      item_count: 3,
      items: [],
    },
  ],
  macro_sections: [
    {
      key: "rates-growth",
      title: "Rates vs growth",
      status: "live",
      description: "Macro comparison for rates and growth.",
      summary: "Growth resilient while rates stabilized.",
      primary: {
        key: "growth",
        label: "Growth",
        status: "live",
        latest_value: "2.4%",
        previous_value: "2.1%",
        change_label: "+0.3 pts",
        trend: "up",
        frequency: "monthly",
        source_label: "BEA",
        source_url: "https://example.com/bea",
        updated_at: "2026-03-30T08:00:00Z",
        period_label: "Mar 2026",
        context: "Real activity held firm.",
        unit: "%",
        points: [],
      },
      secondary: null,
      delta_label: "Spread",
      delta_points: [],
      sources: [],
    },
  ],
  market_sections: [
    {
      key: "qqq",
      label: "QQQ",
      status: "live",
      close_value: "512.4",
      ma20_value: "503.1",
      signal: "Above 20-day average",
      deviation_pct: 1.8,
      trade_date: "2026-03-29",
      source_label: "NASDAQ",
      explanation: "Risk appetite improved overnight.",
      data_window_label: "20 sessions",
      history_warning: "",
      chart_points: [],
    },
  ],
  event_sections: [
    {
      key: "calendar",
      title: "Calendar",
      status: "live",
      items: [
        {
          title: "Fed speaker slate",
          region: "US",
          expected_date: "2026-03-30",
          time_window: "AM",
          confidence: "high",
          impact_summary: "Could reset rate expectations.",
          source: "Federal Reserve",
        },
      ],
      official_links: [],
    },
  ],
  data_status: [
    {
      key: "news-coverage",
      label: "News coverage",
      status: "live",
      detail: "128 stories indexed in the last 24 hours.",
    },
  ],
};

const macroPayload = {
  generated_at: "2026-03-30T09:00:00Z",
  module: {
    id: "macro",
    label: "Macro Intelligence",
    note: "1 comparison card",
    description: "Official macro comparisons with source links.",
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
            points: [],
          },
          secondary: null,
          delta_label: "Gap",
          delta_points: [],
          sources: [{ label: "National Bureau of Statistics", url: "https://example.com/cpi" }],
        },
      },
    ],
  },
};

describe("Workbench shell", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("keeps the /news tab state in the URL", async () => {
    window.history.pushState({}, "", "/news?tab=channels");

    render(<App />);

    expect(await screen.findByRole("link", { name: "Channels" })).toHaveAttribute("aria-current", "page");

    await userEvent.click(screen.getByRole("link", { name: "Sources" }));

    expect(window.location.pathname).toBe("/news");
    expect(window.location.search).toBe("?tab=sources");
    expect(screen.getByRole("link", { name: "Sources" })).toHaveAttribute("aria-current", "page");
  });

  it("renders the Macro route as a real page", async () => {
    window.history.pushState({}, "", "/macro?tab=compare");
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(macroPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Inflation vs growth" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Compare" })).toHaveAttribute("aria-current", "page");
  });

  it("falls back to overview when the tab query is unknown", async () => {
    window.history.pushState({}, "", "/news?tab=unknown");

    render(<App />);

    expect(await screen.findByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");
  });

  it("converges the root path to /dashboard", async () => {
    window.history.pushState({}, "", "/");
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(dashboardPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/dashboard");
  });
});
