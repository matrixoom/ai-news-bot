import { vi } from "vitest";

type WorkbenchPayloads = {
  dashboard: Record<string, unknown>;
  news: Record<string, unknown>;
  macro: Record<string, unknown>;
  market: Record<string, unknown>;
  events: Record<string, unknown>;
  push: Record<string, unknown>;
  macroData: Record<string, unknown>;
  macroChart: Record<string, unknown>;
  eventOutlook: Record<string, unknown>;
  eventInsight: Record<string, unknown>;
  llmProviders: Record<string, unknown>;
  llmTaskConfigs: Record<string, unknown>;
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
            market_chart_range: "1y",
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
            market_chart_range: "1y",
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

export const macroDataPayload: WorkbenchPayloads["macroData"] = {
  generated_at: "2026-05-01T08:00:00Z",
  module: {
    id: "macro-data",
    label: "Macro Data",
    description: "GDP, credit, climate, trade, and inflation indicators",
    status: "live",
    loading: false,
  },
  tabs: [
    { value: "gdp", label: "GDP" },
    { value: "credit", label: "信贷" },
    { value: "climate", label: "景气" },
    { value: "trade", label: "外贸" },
    { value: "prices", label: "物价" },
    { value: "currency", label: "货币" },
    { value: "expectations", label: "预期" },
    { value: "employment", label: "就业" },
  ],
  tab: "gdp",
  default_range: "1y",
  default_frequency: "quarterly",
  frequency_options: [
    { value: "quarterly", label: "季度" },
    { value: "yearly", label: "年度" },
  ],
  range_options: [
    { value: "6m", label: "半年" },
    { value: "1y", label: "1年" },
    { value: "3y", label: "3年" },
    { value: "5y", label: "5年" },
    { value: "10y", label: "10年" },
    { value: "15y", label: "15年" },
    { value: "20y", label: "20年" },
    { value: "25y", label: "25年" },
    { value: "30y", label: "30年" },
    { value: "custom", label: "自定义" },
  ],
  charts: [
    { id: "gdp_total_combined", title: "名义与实际GDP总量", unit: "亿元", frequency: "quarterly", status: "sample", chart_type: "line" },
    { id: "gdp_growth", title: "GDP增速", unit: "%", frequency: "quarterly", status: "sample", chart_type: "line" },
  ],
};

const creditMacroDataPayload: WorkbenchPayloads["macroData"] = {
  generated_at: "2026-05-01T08:00:00Z",
  module: {
    id: "macro-data",
    label: "Macro Data",
    description: "GDP, credit, leverage, and inflation indicators",
    status: "live",
    loading: false,
  },
  tabs: [
    { value: "gdp", label: "GDP" },
    { value: "credit", label: "信贷" },
    { value: "climate", label: "景气" },
    { value: "trade", label: "外贸" },
    { value: "prices", label: "物价" },
    { value: "currency", label: "货币" },
    { value: "expectations", label: "预期" },
    { value: "employment", label: "就业" },
  ],
  tab: "credit",
  default_range: "1y",
  default_frequency: "monthly",
  frequency_options: [
    { value: "monthly", label: "月度" },
    { value: "quarterly", label: "季度" },
    { value: "yearly", label: "年度" },
  ],
  range_options: [
    { value: "6m", label: "半年" },
    { value: "1y", label: "1年" },
    { value: "3y", label: "3年" },
    { value: "5y", label: "5年" },
    { value: "10y", label: "10年" },
    { value: "15y", label: "15年" },
    { value: "20y", label: "20年" },
    { value: "25y", label: "25年" },
    { value: "30y", label: "30年" },
    { value: "custom", label: "自定义" },
  ],
  charts: [
    { id: "new_rmb_loans", title: "新增人民币贷款", unit: "亿元", frequency: "monthly", status: "live", chart_type: "bar_stacked_line", wide: true },
    { id: "household_demand_deposits", title: "居民活期存款", unit: "亿元", frequency: "monthly", status: "live", chart_type: "bar_stacked_line", wide: true },
    { id: "social_financing", title: "社会融资规模", unit: "亿元", frequency: "monthly", status: "live", chart_type: "line", wide: true },
    { id: "household_leverage_ratio", title: "居民部门杠杆率", unit: "%", frequency: "quarterly", status: "live", chart_type: "line" },
    { id: "corporate_leverage_ratio", title: "企业部门杠杆率", unit: "%", frequency: "quarterly", status: "live", chart_type: "line" },
  ],
};

export const macroChartPayload: WorkbenchPayloads["macroChart"] = {
  id: "nominal_gdp",
  title: "名义GDP",
  unit: "亿元",
  frequency: "quarterly",
  status: "sample",
  range: {
    type: "1y",
    start_date: "2025-05-01",
    end_date: "2026-05-01",
  },
  sync_state: {
    status: "sample",
    synced_at: "2026-05-01T08:00:00Z",
    warning_message: "sample data",
    point_count: 2,
  },
  series: [
    {
      name: "名义GDP",
      points: [
        { date: "2025-12-31", period_label: "2025Q4", value: 1260000, unit: "亿元", released_at: "" },
        { date: "2026-03-31", period_label: "2026Q1", value: 322000, unit: "亿元", released_at: "" },
      ],
    },
  ],
};

export const eventOutlookPayload: WorkbenchPayloads["eventOutlook"] = {
  generated_at: "2026-05-05T12:00:00Z",
  module: {
    id: "event-outlook",
    title: "Event Outlook",
    description: "Forward calendar for technology, policy, and finance events.",
  },
  region: "domestic",
  tabs: [
    { value: "domestic", label: "国内" },
    { value: "international", label: "国际" },
  ],
  range: {
    start_date: "2026-05-05",
    end_date: "2027-05-05",
  },
  resolution_options: [
    { value: "day", label: "天" },
    { value: "week", label: "周" },
    { value: "month", label: "月" },
  ],
  events: [
    {
      id: 1,
      region: "domestic",
      event_date: "2026-06-02",
      title: "COMPUTEX 2026",
      summary: "台北国际电脑展，聚焦 AI、机器人、半导体与下一代计算。",
      category: "technology",
      source_name: "COMPUTEX",
      source_url: "https://www.computextaipei.com.tw/en/news/8F914C77B6AF77A5/info.html?cid=news&cr=5&lt=data",
      updated_at: "2026-05-05T12:00:00Z",
    },
    {
      id: 2,
      region: "domestic",
      event_date: "2026-06-02",
      title: "Microsoft Build 2026",
      summary: "开发者大会，关注 Azure、GitHub 与 AI 应用构建。",
      category: "technology",
      source_name: "Microsoft",
      source_url: "https://www.microsoft.com/en-us/startups/blog/microsoft-build-2026-sessions-every-startup-should-attend/",
      updated_at: "2026-05-05T12:00:00Z",
    },
    {
      id: 3,
      region: "domestic",
      event_date: "2026-06-23",
      title: "夏季达沃斯 2026",
      summary: "世界经济论坛新领军者年会，关注新增长模式、全球经济和中国经济前景。",
      category: "finance",
      source_name: "World Economic Forum",
      source_url: "https://www.weforum.org/meetings/annual-meeting-of-the-new-champions-2026/about/",
      updated_at: "2026-05-05T12:00:00Z",
    },
    {
      id: 4,
      region: "domestic",
      event_date: "2026-11-18",
      title: "APEC 领导人非正式会议",
      summary: "第三十三次 APEC 领导人非正式会议将在深圳举行。",
      category: "politics",
      source_name: "中国政府网",
      source_url: "https://english.www.gov.cn/news/202512/12/content_WS693c1432c6d00ca5f9a080e6.html",
      updated_at: "2026-05-05T12:00:00Z",
    },
  ],
};

export const eventInsightPayload: WorkbenchPayloads["eventInsight"] = {
  traceId: "event-insight-events-mock",
  page: 1,
  pageSize: 20,
  total: 2,
  items: [
    {
      id: 1,
      title: "HBM4 量产节奏提前",
      summary: "先进封装产能继续吃紧，AI 加速卡供应链进入新一轮扩产窗口。",
      eventTime: "2026-05-10T09:00:00+08:00",
      eventType: "capacity",
      confidenceScore: 0.86,
      evidenceLevel: "B",
      manualStatus: "active",
      analysisStatus: "extracted",
      graphStatus: "pending",
      sourceMethod: "manual",
      topics: [{ id: 1, name: "AI 存储与封装", roleInTopic: "key_catalyst" }],
    },
    {
      id: 2,
      title: "欧洲云服务厂商扩大主权云采购规模",
      summary: "主权云采购规模上修，带动本地数据中心与安全合规方案需求。",
      eventTime: "2026-05-11T10:00:00+08:00",
      eventType: "supply_demand",
      confidenceScore: 0.74,
      evidenceLevel: "C",
      manualStatus: "active",
      analysisStatus: "extracted",
      graphStatus: "pending",
      sourceMethod: "manual",
      topics: [],
    },
  ],
};

export const llmProvidersPayload: WorkbenchPayloads["llmProviders"] = {
  providers: [
    {
      id: 1,
      name: "主分析模型",
      providerType: "openai_compatible",
      baseUrl: "https://api.example.com/v1",
      modelName: "analysis-model",
      timeoutSeconds: 90,
      supportsStructuredOutput: true,
      supportsEmbeddings: false,
      enabled: true,
      apiKeyConfigured: true,
      apiKeyPreview: "sk-...alue",
    },
  ],
};

export const llmTaskConfigsPayload: WorkbenchPayloads["llmTaskConfigs"] = {
  taskConfigs: [
    {
      taskType: "topic_summary",
      providerId: 1,
      providerName: "主分析模型",
      providerType: "openai_compatible",
      modelName: "analysis-model",
      temperature: 0.2,
      maxTokens: 800,
      enabled: true,
    },
  ],
};

const employmentMacroDataPayload: WorkbenchPayloads["macroData"] = {
  generated_at: "2026-05-01T08:00:00Z",
  module: {
    id: "macro-data",
    label: "Macro Data",
    description: "GDP, credit, climate, trade, prices, currency, expectations, and employment indicators",
    status: "live",
    loading: false,
  },
  tabs: [
    { value: "gdp", label: "GDP" },
    { value: "credit", label: "信贷" },
    { value: "climate", label: "景气" },
    { value: "trade", label: "外贸" },
    { value: "prices", label: "物价" },
    { value: "currency", label: "货币" },
    { value: "expectations", label: "预期" },
    { value: "employment", label: "就业" },
  ],
  tab: "employment",
  default_range: "1y",
  default_frequency: "yearly",
  frequency_options: [
    { value: "monthly", label: "月度" },
    { value: "quarterly", label: "季度" },
    { value: "yearly", label: "年度" },
  ],
  range_options: [
    { value: "6m", label: "半年" },
    { value: "1y", label: "1年" },
    { value: "3y", label: "3年" },
    { value: "5y", label: "5年" },
    { value: "10y", label: "10年" },
    { value: "15y", label: "15年" },
    { value: "20y", label: "20年" },
    { value: "25y", label: "25年" },
    { value: "30y", label: "30年" },
    { value: "custom", label: "自定义" },
  ],
  charts: [
    {
      id: "unemployment_insurance_fund_expense",
      title: "中国社会保险基金支出:失业保险:累计值",
      unit: "亿元",
      frequency: "yearly",
      status: "live",
      chart_type: "line",
    },
  ],
};

export function installWorkbenchFetchMock(overrides: WorkbenchOverrides = {}) {
  const payloads: WorkbenchPayloads = {
    dashboard: overrides.dashboard ?? dashboardPayload,
    news: overrides.news ?? newsPayload,
    macro: overrides.macro ?? macroPayload,
    market: overrides.market ?? marketPayload,
    events: overrides.events ?? eventsPayload,
    push: overrides.push ?? pushPayload,
    macroData: overrides.macroData ?? macroDataPayload,
    macroChart: overrides.macroChart ?? macroChartPayload,
    eventOutlook: overrides.eventOutlook ?? eventOutlookPayload,
    eventInsight: overrides.eventInsight ?? eventInsightPayload,
    llmProviders: overrides.llmProviders ?? llmProvidersPayload,
    llmTaskConfigs: overrides.llmTaskConfigs ?? llmTaskConfigsPayload,
  };

  let pushState: any = clone(payloads.push);
  let eventOutlookState: any = clone(payloads.eventOutlook);
  let llmProvidersState: any = clone(payloads.llmProviders);
  let rssState: any = {
    sources: [],
    scheduler: { enabled: true, timezone: "Asia/Shanghai", dailyFetchTime: "06:30" },
  };

  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const rawUrl = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const url = new URL(rawUrl, window.location.origin);
    const method = init?.method ?? (input instanceof Request ? input.method : "GET");

    if (url.pathname === "/api/frontend/modules/push") {
      return jsonResponse(pushState);
    }

    if (url.pathname === "/api/system/llm/providers" && method === "GET") {
      return jsonResponse(llmProvidersState);
    }

    if (url.pathname === "/api/system/llm/providers" && method === "POST") {
      const body = await readJsonBody(input, init?.body);
      const apiKey = String(body.apiKey ?? "");
      const provider = {
        id: llmProvidersState.providers.length + 1,
        name: body.name,
        providerType: body.providerType ?? "openai_compatible",
        baseUrl: body.baseUrl ?? "",
        modelName: body.modelName,
        timeoutSeconds: body.timeoutSeconds ?? 60,
        supportsStructuredOutput: true,
        supportsEmbeddings: false,
        enabled: true,
        apiKeyConfigured: Boolean(apiKey),
        apiKeyPreview: apiKey ? `${apiKey.slice(0, 3)}...${apiKey.slice(-4)}` : "",
      };
      llmProvidersState = { providers: [...llmProvidersState.providers, provider] };
      return jsonResponse({ provider });
    }

    if (url.pathname.match(/^\/api\/system\/llm\/providers\/\d+$/) && method === "PUT") {
      const providerId = Number(url.pathname.split("/").pop());
      const body = await readJsonBody(input, init?.body);
      const provider = llmProvidersState.providers.find((item: any) => item.id === providerId);
      Object.assign(provider, {
        name: body.name ?? provider.name,
        providerType: body.providerType ?? provider.providerType,
        baseUrl: body.baseUrl ?? provider.baseUrl,
        modelName: body.modelName ?? provider.modelName,
        timeoutSeconds: body.timeoutSeconds ?? provider.timeoutSeconds,
      });
      return jsonResponse({ provider });
    }

    if (url.pathname.match(/^\/api\/system\/llm\/providers\/\d+\/disable$/) && method === "POST") {
      const providerId = Number(url.pathname.split("/").at(-2));
      const provider = llmProvidersState.providers.find((item: any) => item.id === providerId);
      if (provider) provider.enabled = false;
      return jsonResponse({ provider });
    }

    if (url.pathname.match(/^\/api\/system\/llm\/providers\/\d+\/test$/) && method === "POST") {
      const providerId = Number(url.pathname.split("/").at(-2));
      const provider = llmProvidersState.providers.find((item: any) => item.id === providerId);
      return jsonResponse({
        ok: true,
        detail: `连接测试成功：${provider?.name ?? "provider"} / ${provider?.modelName ?? ""} 已返回响应。`,
      });
    }

    if (url.pathname === "/api/system/llm/task-configs" && method === "GET") {
      return jsonResponse(payloads.llmTaskConfigs);
    }

    if (url.pathname === "/api/system/rss/sources" && method === "GET") {
      return jsonResponse(rssState);
    }

    if (url.pathname === "/api/system/rss/sources" && method === "POST") {
      const body = await readJsonBody(input, init?.body);
      const source = {
        id: rssState.sources.length + 1,
        name: body.name,
        url: body.url,
        language: body.language ?? "zh",
        category: body.category ?? "finance",
        enabled: true,
        fetchTime: body.fetchTime ?? "06:30",
        maxItems: body.maxItems ?? 20,
      };
      rssState = { ...rssState, sources: [...rssState.sources, source] };
      return jsonResponse({ source });
    }

    if (url.pathname.match(/^\/api\/system\/rss\/sources\/\d+\/fetch$/) && method === "POST") {
      const sourceId = Number(url.pathname.split("/").at(-2));
      const source = rssState.sources.find((item: any) => item.id === sourceId);
      return jsonResponse({ source, importedCount: 1, skippedCount: 0, fetchedAt: "2026-06-03T08:00:00Z" });
    }

    if (url.pathname === "/api/frontend/modules/event-insight/events" && method === "GET") {
      return jsonResponse(payloads.eventInsight);
    }

    if (url.pathname.startsWith("/api/frontend/modules/event-insight/events/") && method === "GET") {
      const eventId = Number(url.pathname.split("/").pop());
      const events = payloads.eventInsight.items as Array<Record<string, unknown>>;
      const event = events.find((item) => Number(item.id) === eventId) ?? events[0];
      return jsonResponse({
        traceId: "event-insight-event-mock",
        event: {
          ...event,
          evidence: [
            {
              id: 1,
              excerpt: "AI 加速卡供应链进入新一轮扩产窗口。",
              sourceTitle: "Event Insight Mock",
              sourceUrl: "https://example.com/event-insight",
              evidenceLevel: "B",
              role: "primary",
            },
          ],
        },
      });
    }

    if (url.pathname === "/api/frontend/modules/event-outlook") {
      const region = url.searchParams.get("region") ?? "domestic";
      const source = region === "international"
        ? {
            ...eventOutlookState,
            region,
            events: [
              {
                id: 11,
                region: "international",
                event_date: "2026-05-19",
                title: "Google I/O 2026",
                summary: "Google 年度开发者大会，关注 Gemini、Android 与云端 AI 能力。",
                category: "technology",
                source_name: "Google I/O",
                source_url: "https://io.google/2026/",
                updated_at: "2026-05-05T12:00:00Z",
              },
              {
                id: 12,
                region: "international",
                event_date: "2026-06-16",
                title: "FOMC 利率会议",
                summary: "美联储 FOMC 议息会议，关注政策路径和经济预测摘要。",
                category: "finance",
                source_name: "Federal Reserve",
                source_url: "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
                updated_at: "2026-05-05T12:00:00Z",
              },
            ],
          }
        : eventOutlookState;
      return jsonResponse(source);
    }

    if (url.pathname === "/api/frontend/modules/event-outlook/events" && method === "POST") {
      const body = await readJsonBody(input, init?.body);
      const event = {
        id: 99,
        region: body.region ?? "domestic",
        event_date: body.event_date,
        title: body.title,
        summary: body.summary,
        category: body.category ?? "technology",
        source_name: body.source_name ?? "manual",
        source_url: body.source_url ?? "",
        updated_at: "2026-05-05T12:05:00Z",
      };
      eventOutlookState = {
        ...eventOutlookState,
        events: [event, ...eventOutlookState.events],
      };
      return jsonResponse({ event });
    }

    if (url.pathname.startsWith("/api/frontend/modules/event-outlook/events/") && method === "PUT") {
      const body = await readJsonBody(input, init?.body);
      const eventId = Number(url.pathname.split("/").pop());
      const existing = eventOutlookState.events.find((event: any) => event.id === eventId) ?? eventOutlookState.events[0];
      const event = {
        ...existing,
        title: body.title ?? existing.title,
        summary: body.summary ?? existing.summary,
        updated_at: "2026-05-05T12:10:00Z",
      };
      eventOutlookState = {
        ...eventOutlookState,
        events: eventOutlookState.events.map((item: any) => (item.id === event.id ? event : item)),
      };
      return jsonResponse({ event });
    }

    if (url.pathname === "/api/frontend/modules/macro-data") {
      const tab = url.searchParams.get("tab") ?? "gdp";
      if (tab === "credit") {
        return jsonResponse(creditMacroDataPayload);
      }
      if (tab === "employment") {
        return jsonResponse(employmentMacroDataPayload);
      }
      return jsonResponse(payloads.macroData);
    }

    if (url.pathname.startsWith("/api/frontend/modules/macro-data/charts/")) {
      const chartId = url.pathname.split("/").pop() ?? "nominal_gdp";
      if (chartId === "gdp_total_combined") {
        return jsonResponse({
          ...payloads.macroChart,
          id: chartId,
          title: "名义与实际GDP总量",
          unit: "亿元",
          series: [
            {
              name: "名义GDP",
              points: [
                { date: "2025-12-31", period_label: "2025Q4", value: 1260000, unit: "亿元", released_at: "" },
                { date: "2026-03-31", period_label: "2026Q1", value: 322000, unit: "亿元", released_at: "" },
              ],
            },
            {
              name: "实际GDP",
              points: [
                { date: "2025-12-31", period_label: "2025Q4", value: 1100000, unit: "亿元", released_at: "" },
                { date: "2026-03-31", period_label: "2026Q1", value: 305000, unit: "亿元", released_at: "" },
              ],
            },
          ],
          range: {
            ...(payloads.macroChart.range as Record<string, unknown>),
            type: url.searchParams.get("range") ?? "1y",
          },
          frequency: url.searchParams.get("frequency") ?? "quarterly",
        });
      }
      if (chartId === "gdp_growth") {
        return jsonResponse({
          ...payloads.macroChart,
          id: chartId,
          title: "GDP增速",
          unit: "%",
          series: [
            {
              name: "名义GDP增速",
              points: [{ date: "2026-03-31", period_label: "2026Q1", value: 3.87, unit: "%", released_at: "" }],
            },
            {
              name: "实际GDP增速",
              points: [{ date: "2026-03-31", period_label: "2026Q1", value: 4.75, unit: "%", released_at: "" }],
            },
          ],
          range: {
            ...(payloads.macroChart.range as Record<string, unknown>),
            type: url.searchParams.get("range") ?? "1y",
          },
          frequency: url.searchParams.get("frequency") ?? "quarterly",
        });
      }
      if (chartId === "currency_supply") {
        return jsonResponse({
          ...payloads.macroChart,
          id: chartId,
          title: "货币供应量",
          unit: "亿元",
          frequency: "monthly",
          series: [
            {
              name: "M0",
              points: [
                { date: "2025-11-30", period_label: "2025-11", value: 121000, unit: "亿元", released_at: "" },
                { date: "2025-12-31", period_label: "2025-12", value: 124000, unit: "亿元", released_at: "" },
                { date: "2026-01-31", period_label: "2026-01", value: 128000, unit: "亿元", released_at: "" },
                { date: "2026-02-28", period_label: "2026-02", value: 125000, unit: "亿元", released_at: "" },
                { date: "2026-03-31", period_label: "2026-03", value: 130000, unit: "亿元", released_at: "" },
              ],
            },
            {
              name: "M1",
              points: [
                { date: "2025-11-30", period_label: "2025-11", value: 735000, unit: "亿元", released_at: "" },
                { date: "2025-12-31", period_label: "2025-12", value: 742000, unit: "亿元", released_at: "" },
                { date: "2026-01-31", period_label: "2026-01", value: 751000, unit: "亿元", released_at: "" },
                { date: "2026-02-28", period_label: "2026-02", value: 738000, unit: "亿元", released_at: "" },
                { date: "2026-03-31", period_label: "2026-03", value: 756000, unit: "亿元", released_at: "" },
              ],
            },
            {
              name: "M2",
              points: [
                { date: "2025-11-30", period_label: "2025-11", value: 3110000, unit: "亿元", released_at: "" },
                { date: "2025-12-31", period_label: "2025-12", value: 3140000, unit: "亿元", released_at: "" },
                { date: "2026-01-31", period_label: "2026-01", value: 3180000, unit: "亿元", released_at: "" },
                { date: "2026-02-28", period_label: "2026-02", value: 3130000, unit: "亿元", released_at: "" },
                { date: "2026-03-31", period_label: "2026-03", value: 3220000, unit: "亿元", released_at: "" },
              ],
            },
          ],
          range: {
            ...(payloads.macroChart.range as Record<string, unknown>),
            type: url.searchParams.get("range") ?? "1y",
          },
        });
      }
      if (chartId === "social_financing") {
        return jsonResponse({
          ...payloads.macroChart,
          id: chartId,
          title: "社会融资规模",
          unit: "亿元",
          frequency: "monthly",
          wide: true,
          series: [
            { name: "社会融资规模", points: [
              { date: "2025-11-30", period_label: "2025-11", value: 28000, unit: "亿元", released_at: "" },
              { date: "2025-12-31", period_label: "2025-12", value: 61000, unit: "亿元", released_at: "" },
              { date: "2026-01-31", period_label: "2026-01", value: 12000, unit: "亿元", released_at: "" },
              { date: "2026-02-28", period_label: "2026-02", value: 45000, unit: "亿元", released_at: "" },
            ]},
          ],
          range: {
            ...(payloads.macroChart.range as Record<string, unknown>),
            type: url.searchParams.get("range") ?? "1y",
          },
        });
      }
      if (chartId === "household_demand_deposits") {
        return jsonResponse({
          ...payloads.macroChart,
          id: chartId,
          title: "居民活期存款",
          unit: "亿元",
          frequency: "monthly",
          chart_type: "bar_stacked_line",
          wide: true,
          series: [
            { name: "居民存款总计", points: [
              { date: "2000-01-31", period_label: "2000-01", value: 60241.8, unit: "亿元", released_at: "" },
              { date: "2026-03-31", period_label: "2026-03", value: 1735889.52, unit: "亿元", released_at: "" },
            ]},
            { name: "居民活期存款", points: [
              { date: "2000-01-31", period_label: "2000-01", value: 14975, unit: "亿元", released_at: "" },
              { date: "2026-03-31", period_label: "2026-03", value: 420190.26, unit: "亿元", released_at: "" },
            ]},
            { name: "居民定期及其他存款", points: [
              { date: "2000-01-31", period_label: "2000-01", value: 45266.8, unit: "亿元", released_at: "" },
              { date: "2026-03-31", period_label: "2026-03", value: 1315699.26, unit: "亿元", released_at: "" },
            ]},
          ],
          range: {
            ...(payloads.macroChart.range as Record<string, unknown>),
            type: url.searchParams.get("range") ?? "1y",
          },
        });
      }
      if (chartId === "household_leverage_ratio") {
        return jsonResponse({
          ...payloads.macroChart,
          id: chartId,
          title: "居民部门杠杆率",
          unit: "%",
          frequency: "quarterly",
          series: [
            {
              name: "居民部门杠杆率",
              points: [
                { date: "2025-09-30", period_label: "2025Q3", value: 62.3, unit: "%", released_at: "" },
                { date: "2025-12-31", period_label: "2025Q4", value: 63.1, unit: "%", released_at: "" },
              ],
            },
          ],
          range: {
            ...(payloads.macroChart.range as Record<string, unknown>),
            type: url.searchParams.get("range") ?? "1y",
          },
        });
      }
      if (chartId === "corporate_leverage_ratio") {
        return jsonResponse({
          ...payloads.macroChart,
          id: chartId,
          title: "企业部门杠杆率",
          unit: "%",
          frequency: "quarterly",
          series: [
            {
              name: "企业部门杠杆率",
              points: [
                { date: "2025-09-30", period_label: "2025Q3", value: 168.5, unit: "%", released_at: "" },
                { date: "2025-12-31", period_label: "2025Q4", value: 170.2, unit: "%", released_at: "" },
              ],
            },
          ],
          range: {
            ...(payloads.macroChart.range as Record<string, unknown>),
            type: url.searchParams.get("range") ?? "1y",
          },
        });
      }
      if (chartId === "new_rmb_loans") {
        return jsonResponse({
          ...payloads.macroChart,
          id: chartId,
          title: "新增人民币贷款",
          unit: "亿元",
          frequency: "monthly",
          chart_type: "bar_stacked_line",
          wide: true,
          series: [
            { name: "居民新增短期贷款", points: [
              { date: "2025-11-30", period_label: "2025-11", value: 3200, unit: "亿元", released_at: "" },
              { date: "2025-12-31", period_label: "2025-12", value: 4100, unit: "亿元", released_at: "" },
              { date: "2026-01-31", period_label: "2026-01", value: 6200, unit: "亿元", released_at: "" },
              { date: "2026-02-28", period_label: "2026-02", value: 2800, unit: "亿元", released_at: "" },
            ]},
            { name: "居民新增长期贷款", points: [
              { date: "2025-11-30", period_label: "2025-11", value: 9800, unit: "亿元", released_at: "" },
              { date: "2025-12-31", period_label: "2025-12", value: 8500, unit: "亿元", released_at: "" },
              { date: "2026-01-31", period_label: "2026-01", value: 14300, unit: "亿元", released_at: "" },
              { date: "2026-02-28", period_label: "2026-02", value: 9100, unit: "亿元", released_at: "" },
            ]},
            { name: "企业新增短期贷款", points: [
              { date: "2025-11-30", period_label: "2025-11", value: 7600, unit: "亿元", released_at: "" },
              { date: "2025-12-31", period_label: "2025-12", value: 8500, unit: "亿元", released_at: "" },
              { date: "2026-01-31", period_label: "2026-01", value: 14300, unit: "亿元", released_at: "" },
              { date: "2026-02-28", period_label: "2026-02", value: 9100, unit: "亿元", released_at: "" },
            ]},
            { name: "企业新增长期贷款", points: [
              { date: "2025-11-30", period_label: "2025-11", value: 14200, unit: "亿元", released_at: "" },
              { date: "2025-12-31", period_label: "2025-12", value: 12800, unit: "亿元", released_at: "" },
              { date: "2026-01-31", period_label: "2026-01", value: 19500, unit: "亿元", released_at: "" },
              { date: "2026-02-28", period_label: "2026-02", value: 11500, unit: "亿元", released_at: "" },
            ]},
          ],
          range: {
            ...(payloads.macroChart.range as Record<string, unknown>),
            type: url.searchParams.get("range") ?? "1y",
          },
        });
      }
      if (chartId === "unemployment_insurance_fund_expense") {
        return jsonResponse({
          ...payloads.macroChart,
          id: chartId,
          title: "中国社会保险基金支出:失业保险:累计值",
          unit: "亿元",
          frequency: url.searchParams.get("frequency") ?? "yearly",
          series: [
            {
              name: "中国社会保险基金支出:失业保险:累计值",
              points: [
                { date: "2005-12-31", period_label: "2005", value: 206.9, unit: "亿元", released_at: "" },
                { date: "2006-12-31", period_label: "2006", value: 198.0, unit: "亿元", released_at: "" },
                { date: "2007-12-31", period_label: "2007", value: 217.6, unit: "亿元", released_at: "" },
                { date: "2008-12-31", period_label: "2008", value: 253.5, unit: "亿元", released_at: "" },
                { date: "2009-12-31", period_label: "2009", value: 366.8, unit: "亿元", released_at: "" },
                { date: "2010-12-31", period_label: "2010", value: 423.3, unit: "亿元", released_at: "" },
                { date: "2011-12-31", period_label: "2011", value: 432.8, unit: "亿元", released_at: "" },
                { date: "2012-12-31", period_label: "2012", value: 450.6, unit: "亿元", released_at: "" },
                { date: "2013-12-31", period_label: "2013", value: 531.6, unit: "亿元", released_at: "" },
                { date: "2014-12-31", period_label: "2014", value: 614.7, unit: "亿元", released_at: "" },
                { date: "2015-12-31", period_label: "2015", value: 736.4, unit: "亿元", released_at: "" },
                { date: "2016-12-31", period_label: "2016", value: 976.1, unit: "亿元", released_at: "" },
                { date: "2017-12-31", period_label: "2017", value: 893.8, unit: "亿元", released_at: "" },
                { date: "2018-12-31", period_label: "2018", value: 915.3, unit: "亿元", released_at: "" },
                { date: "2019-12-31", period_label: "2019", value: 1333.2, unit: "亿元", released_at: "" },
                { date: "2020-12-31", period_label: "2020", value: 2103.0, unit: "亿元", released_at: "" },
                { date: "2021-12-31", period_label: "2021", value: 1500.0, unit: "亿元", released_at: "" },
                { date: "2022-12-31", period_label: "2022", value: 2017.8, unit: "亿元", released_at: "" },
                { date: "2023-12-31", period_label: "2023", value: 1485.2, unit: "亿元", released_at: "" },
                { date: "2024-12-31", period_label: "2024", value: 1842.0, unit: "亿元", released_at: "" },
              ],
            },
          ],
          range: {
            ...(payloads.macroChart.range as Record<string, unknown>),
            type: url.searchParams.get("range") ?? "1y",
          },
        });
      }
      return jsonResponse({
        ...payloads.macroChart,
        id: chartId,
        title: chartId === "real_gdp" ? "实际GDP" : payloads.macroChart.title,
        series: [
          {
            ...(payloads.macroChart.series as Array<Record<string, unknown>>)[0],
            name: chartId === "real_gdp" ? "实际GDP" : "名义GDP",
          },
        ],
        range: {
          ...(payloads.macroChart.range as Record<string, unknown>),
          type: url.searchParams.get("range") ?? "1y",
        },
        frequency: url.searchParams.get("frequency") ?? "quarterly",
      });
    }

    if (url.pathname.startsWith("/api/frontend/modules/macro-data/sync/") && method === "POST") {
      return jsonResponse({ ok: true, point_counts: { "indicator": 5 } });
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
        market_chart_range: unwrapped.market_chart_range ?? "1y",
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

    if (url.pathname === "/api/push/market-chart-refresh" && method === "POST") {
      return jsonResponse({
        job: {
          id: "market-chart-refresh-1",
          status: "running",
          completed: 2,
          total: 6,
          percentage: 33,
          current_symbol: "CSI500",
          current_label: "中证500",
          message: "正在刷新 中证500。",
          errors: [],
        },
      });
    }

    if (url.pathname === "/api/push/market-chart-refresh/market-chart-refresh-1" && method === "GET") {
      const preview = {
        ...pushState.module.details[0].section.preview,
        generated_at: "2026-03-30T09:13:00Z",
        subject: "Charts refreshed",
        html_body: "<html><body><h1>Charts refreshed</h1></body></html>",
      };
      return jsonResponse({
        job: {
          id: "market-chart-refresh-1",
          status: "completed",
          completed: 6,
          total: 6,
          percentage: 100,
          current_symbol: "HSTECH",
          current_label: "恒生科技指数",
          message: "最近三个月宽基指数历史已刷新，预览图已重绘。",
          errors: [],
          preview,
        },
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
