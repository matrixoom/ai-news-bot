import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../app";
import { AppProviders } from "../providers";
import { appRoutes } from "../routes";

const dashboardPayload = {
  generated_at: "2026-03-30T09:00:00Z",
  news_mode: "hybrid",
  news_mode_options: [{ value: "hybrid", label: "Hybrid" }],
  upstream_service_status: "available",
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

describe("Workbench shell", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the sidebar and the active route title", async () => {
    const router = createMemoryRouter(appRoutes, {
      initialEntries: ["/news"],
    });

    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>,
    );

    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Push Center" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "News" })).toBeInTheDocument();
    expect(screen.getByText("Module page coming in the next slice.")).toBeInTheDocument();
  });

  it("renders the dashboard route with the shared placeholder", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(dashboardPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const router = createMemoryRouter(appRoutes, {
      initialEntries: ["/dashboard"],
    });

    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>,
    );

    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(await screen.findByText("Today Brief")).toBeInTheDocument();
  });

  it("uses the real App entry to keep URL and title in sync", async () => {
    window.history.pushState({}, "", "/news");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "News" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("link", { name: "Dashboard" }));

    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/dashboard");
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
