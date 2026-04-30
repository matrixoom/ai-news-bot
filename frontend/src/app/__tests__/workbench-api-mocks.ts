import { vi } from "vitest";

type WorkbenchPayloads = {
  dashboard: Record<string, unknown>;
  news: Record<string, unknown>;
  macro: Record<string, unknown>;
  market: Record<string, unknown>;
  events: Record<string, unknown>;
  push: Record<string, unknown>;
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
  macro_sections: clone(dashboardPayload.macro_sections),
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

export const pushPayload: WorkbenchPayloads["push"] = {
  generated_at: "2026-03-30T09:00:00Z",
  refresh_after_ms: 30000,
  module: {
    id: "push",
    label: "Push Center",
    note: "1 schedule / 1 module",
    description: "Configure delivery channels, preview the report, and manage schedules.",
    status: "compatible",
    loading: false,
    details: [
      {
        id: "workspace",
        label: "Push workspace",
        kind: "push",
        note: "1 schedule / 1 module",
        section: {
          channel_type_options: [
            {
              id: "email",
              label: "Email",
              enabled: true,
              description: "SMTP delivery for recurring reports.",
            },
          ],
          source_module_options: [
            {
              id: "market",
              label: "Market",
              enabled: true,
              push_ready: true,
              description: "Primary module for the report.",
            },
            {
              id: "news",
              label: "News",
              enabled: false,
              push_ready: false,
              description: "Reserved for a follow-up slice.",
            },
          ],
          style_options: [
            {
              id: "newspaper",
              label: "Newspaper",
              recommended: true,
              description: "Two-column daily briefing.",
            },
            {
              id: "briefing",
              label: "Briefing",
              recommended: false,
              description: "Compact single-column summary.",
            },
          ],
          config_path: ".data/push_center.json",
          config: {
            selected_module_ids: ["market"],
            report_style: "newspaper",
            email: {
              enabled: true,
              label: "Primary Email",
              smtp_server: "smtp.example.com",
              smtp_port: 587,
              use_tls: true,
              username: "bot@example.com",
              password: "secret",
              from_address: "bot@example.com",
              to_addresses: "desk@example.com",
              password_configured: true,
            },
            schedules: [
              {
                id: "market-daily",
                name: "Market Daily",
                enabled: true,
                module_ids: ["market"],
                channel_types: ["email"],
                times: ["08:00", "17:00"],
                timezone: "Asia/Shanghai",
              },
            ],
          },
          preview: {
            ok: true,
            generated_at: "2026-03-30T09:00:00Z",
            subject: "Market Daily - 2026-03-30",
            text_body: "# Market Daily",
            html_body: "<html><body><h1>Market Daily</h1></body></html>",
            style: "newspaper",
            selected_module_ids: ["market"],
          },
          recent_runs: [
            {
              executed_at: "2026-03-30T08:00:00+08:00",
              timezone: "Asia/Shanghai",
              trigger: "scheduled",
              job_name: "Market Daily",
              status: "success",
              detail: "Sent",
              subject: "Market Daily - 2026-03-30",
              channel_types: ["email"],
              module_ids: ["market"],
            },
          ],
          scheduler: {
            enabled: true,
            check_interval_seconds: 20,
          },
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
    push: overrides.push ?? pushPayload,
  };

  let pushState: any = clone(payloads.push);

  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const rawUrl = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const url = new URL(rawUrl, window.location.origin);
    const method = init?.method ?? (input instanceof Request ? input.method : "GET");

    if (url.pathname === "/api/frontend/modules/push") {
      return jsonResponse(pushState);
    }

    if (url.pathname === "/api/push/config" && method === "PUT") {
      const nextConfig = await readJsonBody(input, init?.body);
      const unwrapped = typeof nextConfig?.config === "object" && nextConfig?.config ? nextConfig.config : nextConfig;
      pushState = {
        ...pushState,
        generated_at: "2026-03-30T09:10:00Z",
        module: {
          ...pushState.module,
          details: [
            {
              ...pushState.module.details[0],
              section: {
                ...pushState.module.details[0].section,
                config: clone(unwrapped),
              },
            },
          ],
        },
      };

      return jsonResponse(pushState);
    }

    if (url.pathname === "/api/push/preview" && method === "POST") {
      const nextConfig = await readJsonBody(input, init?.body);
      const unwrapped = typeof nextConfig?.config === "object" && nextConfig?.config ? nextConfig.config : nextConfig;
      const nextPreview = {
        ...pushState.module.details[0].section.preview,
        generated_at: "2026-03-30T09:12:00Z",
        style: unwrapped.report_style ?? "newspaper",
        subject: `Preview for ${unwrapped.report_style ?? "newspaper"}`,
        html_body: `<html><body><h1>${unwrapped.report_style ?? "newspaper"}</h1></body></html>`,
        selected_module_ids: unwrapped.selected_module_ids ?? ["market"],
      };
      pushState = {
        ...pushState,
        module: {
          ...pushState.module,
          details: [
            {
              ...pushState.module.details[0],
              section: {
                ...pushState.module.details[0].section,
                config: clone(unwrapped),
                preview: nextPreview,
              },
            },
          ],
        },
      };

      return jsonResponse({
        generated_at: "2026-03-30T09:12:00Z",
        config: clone(unwrapped),
        preview: nextPreview,
      });
    }

    if (url.pathname === "/api/push/trigger" && method === "POST") {
      const nextConfig = await readJsonBody(input, init?.body);
      const unwrapped = typeof nextConfig?.config === "object" && nextConfig?.config ? nextConfig.config : nextConfig;
      const manualRun = {
        executed_at: "2026-03-30T09:15:00+08:00",
        timezone: "Asia/Shanghai",
        trigger: "manual",
        job_name: "Manual send",
        status: "success",
        detail: "Sent",
        subject: "Manual push",
        channel_types: ["email"],
        module_ids: unwrapped.selected_module_ids ?? ["market"],
      };
      pushState = {
        ...pushState,
        module: {
          ...pushState.module,
          details: [
            {
              ...pushState.module.details[0],
              section: {
                ...pushState.module.details[0].section,
                recent_runs: [manualRun, ...pushState.module.details[0].section.recent_runs],
              },
            },
          ],
        },
      };

      return jsonResponse({
        ok: true,
        preview: clone(pushState.module.details[0].section.preview),
        recent_runs: clone(pushState.module.details[0].section.recent_runs),
        result: {
          status: "success",
          executed_at: manualRun.executed_at,
          timezone: manualRun.timezone,
          trigger: manualRun.trigger,
          job_name: manualRun.job_name,
          sent: ["email"],
          failed: [],
          detail: manualRun.detail,
        },
      });
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

function buildDashboardPayload(payloads: WorkbenchPayloads): Record<string, unknown> {
  const dashboard = clone(payloads.dashboard);

  return {
    ...dashboard,
    news_sections: extractModuleSections(payloads.news, "news", dashboard.news_sections),
    macro_sections: extractMacroSections(payloads.macro, dashboard.macro_sections),
    market_sections: extractModuleSections(payloads.market, "market", dashboard.market_sections),
    event_sections: extractModuleSections(payloads.events, "events", dashboard.event_sections),
  };
}

function extractMacroSections(payload: Record<string, unknown>, fallback: unknown) {
  return Array.isArray(payload.macro_sections) ? payload.macro_sections : fallback;
}

function extractModuleSections(payload: Record<string, unknown>, moduleId: string, fallback: unknown) {
  const module = payload.module as { id?: string; details?: Array<{ section: unknown }> } | undefined;

  if (module?.id !== moduleId || !Array.isArray(module.details)) {
    return fallback;
  }

  return module.details.map((detail) => detail.section);
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

async function readJsonBody(input: RequestInfo | URL, body?: BodyInit | null): Promise<Record<string, any>> {
  if (input instanceof Request) {
    return (await input.clone().json()) as Record<string, any>;
  }

  if (typeof body === "string") {
    return JSON.parse(body) as Record<string, any>;
  }

  return {};
}
