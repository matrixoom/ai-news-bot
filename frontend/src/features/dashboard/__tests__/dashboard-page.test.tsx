import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DashboardPage } from "../../../pages/dashboard-page";

const dashboardPayload = {
  generated_at: "2026-03-30T09:00:00Z",
  news_mode: "hybrid",
  news_mode_options: [
    {
      value: "hybrid",
      label: "Hybrid",
    },
  ],
  upstream_service_status: {
    status: "running",
    healthy: true,
    managed: false,
    is_local: false,
    base_url: "https://newsnow.example.com",
    detail: "upstream service is reachable",
  },
  title: "Trend Insights",
  subtitle: "Technology headlines turned constructive overnight.",
  coverage_note: "128 stories indexed in the last 24 hours.",
  highlights: [
    "Technology headlines turned constructive overnight.",
    "Rate-sensitive sectors held firm into the close.",
  ],
  news_sections: [
    {
      key: "top-news",
      title: "Top News",
      status: "live",
      description: "Leading developments across the news desk.",
      item_count: 3,
      items: [
        {
          rank: 1,
          title: "AI suppliers led the overnight bid.",
          source: "Newswire",
          url: "https://example.com/news/ai-suppliers",
          published_at: "2026-03-30T08:30:00Z",
          tag: "Technology",
          summary: "Momentum rotated back into large-cap AI names.",
          is_placeholder: false,
        },
      ],
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

describe("DashboardPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders KPI cards, brief items, and module snapshots from the API payload", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(dashboardPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <DashboardPage />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Trend Insights")).toBeInTheDocument();
    });

    expect(screen.getByText("Today Brief")).toBeInTheDocument();
    expect(screen.getAllByText("Technology headlines turned constructive overnight.")[0]).toBeInTheDocument();
    expect(screen.getByText("News coverage")).toBeInTheDocument();
    expect(screen.getByText("Module snapshots")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open News" })).toBeInTheDocument();
  });
});
