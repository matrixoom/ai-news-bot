import { vi } from "vitest";

type WorkbenchPayloads = {
  dashboard: Record<string, unknown>;
  news: Record<string, unknown>;
  macro: Record<string, unknown>;
  market: Record<string, unknown>;
  events: Record<string, unknown>;
  status: Record<string, unknown>;
};

type WorkbenchOverrides = Partial<WorkbenchPayloads>;

export const dashboardPayload: WorkbenchPayloads["dashboard"] = {
  generated_at: "2026-03-30T09:00:00Z",
  news_mode: "hybrid",
  news_mode_options: [
    { value: "hybrid", label: "Hybrid" },
    { value: "api", label: "API" },
    { value: "upstream", label: "Upstream" },
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

export const newsPayload: WorkbenchPayloads["news"] = {
  generated_at: "2026-03-30T09:00:00Z",
  news_mode: "hybrid",
  news_mode_options: [
    { value: "hybrid", label: "Hybrid" },
    { value: "api", label: "API" },
    { value: "upstream", label: "Upstream" },
  ],
  upstream_service_status: {
    status: "running",
    healthy: true,
    managed: false,
    is_local: false,
    base_url: "https://newsnow.example.com",
    detail: "upstream service is reachable",
  },
  module: {
    id: "news",
    label: "News Intelligence",
    note: "1 channel, 1 headline",
    description: "Technology, finance, and policy headlines in one calm workbench.",
    status: "live",
    loading: false,
    details: [
      {
        id: "technology",
        label: "Technology",
        kind: "news",
        note: "1 story",
        section: {
          key: "technology",
          title: "Technology",
          status: "live",
          description: "Platform and AI coverage.",
          item_count: 1,
          items: [
            {
              rank: 1,
              title: "AI chip makers extended the overnight bid.",
              source: "Newswire",
              url: "https://example.com/ai-chip-makers",
              published_at: "2026-03-30T08:30:00Z",
              tag: "technology",
              summary: "Large-cap semis led the session higher.",
              is_placeholder: false,
            },
          ],
        },
      },
    ],
  },
};

export const macroPayload: WorkbenchPayloads["macro"] = {
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

export const marketPayload: WorkbenchPayloads["market"] = {
  generated_at: "2026-03-30T09:00:00Z",
  module: {
    id: "market",
    label: "Market Models",
    note: "1 model card",
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
          chart_points: [],
        },
      },
    ],
  },
};

export const eventsPayload: WorkbenchPayloads["events"] = {
  generated_at: "2026-03-30T09:00:00Z",
  module: {
    id: "events",
    label: "Events Outlook",
    note: "1 window card",
    description: "Timeline and watch windows for official calendars.",
    status: "live",
    loading: false,
    details: [
      {
        id: "next-7-days",
        label: "Next 7 Days",
        kind: "events",
        note: "1 item",
        section: {
          key: "next-7-days",
          title: "Next 7 Days",
          status: "live",
          items: [
            {
              title: "Federal Reserve speaker slate",
              region: "US",
              expected_date: "2026-04-02",
              time_window: "All day",
              confidence: "medium",
              impact_summary: "Policy commentary could move rate expectations again.",
              source: "Federal Reserve",
            },
          ],
          official_links: [
            {
              region: "US",
              label: "Federal Reserve Calendar",
              url: "https://www.federalreserve.gov/newsevents/calendar.htm",
            },
          ],
        },
      },
    ],
  },
};

export const statusPayload: WorkbenchPayloads["status"] = {
  generated_at: "2026-03-30T09:00:00Z",
  coverage_note: "128 stories indexed in the last 24 hours.",
  module: {
    id: "status",
    label: "Data Status",
    note: "2 data cards",
    description: "Freshness and source health across the workbench.",
    status: "live",
    loading: false,
    details: [
      {
        id: "news-coverage",
        label: "News coverage",
        kind: "status",
        note: "live",
        section: {
          key: "news-coverage",
          label: "News coverage",
          status: "live",
          detail: "128 stories indexed in the last 24 hours.",
        },
      },
      {
        id: "upstream-health",
        label: "Upstream health",
        kind: "status",
        note: "running",
        section: {
          key: "upstream-health",
          label: "Upstream health",
          status: "live",
          detail: "upstream service is reachable",
        },
      },
    ],
  },
};

export function installWorkbenchFetchMock(overrides: WorkbenchOverrides = {}) {
  const payloads: WorkbenchPayloads = {
    dashboard: overrides.dashboard ?? dashboardPayload,
    news: overrides.news ?? newsPayload,
    macro: overrides.macro ?? macroPayload,
    market: overrides.market ?? marketPayload,
    events: overrides.events ?? eventsPayload,
    status: overrides.status ?? statusPayload,
  };

  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const rawUrl = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const url = new URL(rawUrl, window.location.origin);

    if (url.pathname === "/api/frontend/dashboard") {
      return jsonResponse({
        ...clone(payloads.dashboard),
        news_mode: url.searchParams.get("news_mode") ?? "hybrid",
      });
    }

    if (url.pathname === "/api/frontend/modules/news") {
      return jsonResponse({
        ...clone(payloads.news),
        news_mode: url.searchParams.get("news_mode") ?? "hybrid",
      });
    }

    if (url.pathname === "/api/frontend/modules/macro") {
      return jsonResponse(payloads.macro);
    }

    if (url.pathname === "/api/frontend/modules/market") {
      return jsonResponse(payloads.market);
    }

    if (url.pathname === "/api/frontend/modules/events") {
      return jsonResponse(payloads.events);
    }

    if (url.pathname === "/api/frontend/modules/status") {
      return jsonResponse(payloads.status);
    }

    throw new Error(`Unexpected fetch request for ${url.pathname}`);
  });
}

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}
