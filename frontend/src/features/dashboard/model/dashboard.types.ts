export type DashboardRawPayload = {
  generated_at: string;
  news_mode: string;
  news_mode_options: Array<{
    value: string;
    label: string;
  }>;
  upstream_service_status: string;
  title: string;
  subtitle: string;
  coverage_note: string;
  highlights: string[];
  news_sections: Array<{
    key: string;
    title: string;
    status: string;
    description: string;
    item_count: number;
    items: Array<{
      rank: number;
      title: string;
      source: string;
      url: string;
      published_at: string;
      tag: string;
      summary: string;
      is_placeholder: boolean;
    }>;
  }>;
  macro_sections: Array<{
    key: string;
    title: string;
    status: string;
    description: string;
    summary: string;
    primary: {
      key: string;
      label: string;
      status: string;
      latest_value: string;
      previous_value: string;
      change_label: string;
      trend: string;
      frequency: string;
      source_label: string;
      source_url: string;
      updated_at: string;
      period_label: string;
      context: string;
      unit: string;
      points: Array<{
        period_end: string;
        period_label: string;
        value: number;
      }>;
    };
    secondary: null | {
      key: string;
      label: string;
      status: string;
      latest_value: string;
      previous_value: string;
      change_label: string;
      trend: string;
      frequency: string;
      source_label: string;
      source_url: string;
      updated_at: string;
      period_label: string;
      context: string;
      unit: string;
      points: Array<{
        period_end: string;
        period_label: string;
        value: number;
      }>;
    };
    delta_label: string;
    delta_points: Array<{
      period_end: string;
      period_label: string;
      value: number;
    }>;
    sources: Array<{
      label: string;
      url: string;
    }>;
  }>;
  market_sections: Array<{
    key: string;
    label: string;
    status: string;
    close_value: string;
    ma20_value: string;
    signal: string;
    deviation_pct: number;
    trade_date: string;
    source_label: string;
    explanation: string;
    data_window_label: string;
    history_warning: string;
    chart_points: Array<Record<string, unknown>>;
  }>;
  event_sections: Array<{
    key: string;
    title: string;
    status: string;
    items: Array<{
      title: string;
      region: string;
      expected_date: string;
      time_window: string;
      confidence: string;
      impact_summary: string;
      source: string;
    }>;
    official_links: Array<{
      region: string;
      label: string;
      url: string;
    }>;
  }>;
  data_status: Array<{
    key: string;
    label: string;
    status: string;
    detail: string;
  }>;
};

export type DashboardViewModel = {
  hero: {
    eyebrow: string;
    title: string;
    summary: string;
  };
  stats: Array<{
    id: string;
    label: string;
    value: string;
    change: string;
  }>;
  brief: {
    title: string;
    summary: string;
    ctaLabel: string;
    ctaHref: string;
  };
  moduleSectionTitle: string;
  modules: Array<{
    id: string;
    title: string;
    summary: string;
    ctaLabel: string;
    ctaHref: string;
    status: string;
  }>;
};
