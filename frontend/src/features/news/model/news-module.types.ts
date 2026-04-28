export type NewsUpstreamServiceStatusRaw = {
  status: string;
  healthy: boolean;
  managed: boolean;
  is_local: boolean;
  base_url: string;
  detail: string;
};

export type NewsUpstreamServiceStatus = {
  status: string;
  healthy: boolean;
  managed: boolean;
  isLocal: boolean;
  baseUrl: string;
  detail: string;
  summaryLabel: string;
};

export type NewsModuleRawPayload = {
  generated_at: string;
  news_mode: string;
  news_mode_options: Array<{
    value: string;
    label: string;
  }>;
  upstream_service_status: NewsUpstreamServiceStatusRaw;
  module: {
    id: "news";
    label: string;
    note: string;
    description: string;
    status: string;
    loading: boolean;
    details: Array<{
      id: string;
      label: string;
      kind: "news";
      note: string;
      section: {
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
      };
    }>;
  };
};

export type NewsChannelSummary = {
  id: string;
  title: string;
  status: string;
  description: string;
  itemCount: number;
  note: string;
  topHeadline: string;
};

export type NewsHeadlineView = {
  rank: number;
  title: string;
  source: string;
  url: string;
  publishedAt: string;
  tag: string;
  summary: string;
  channelId: string;
  channelTitle: string;
};

export type NewsModuleViewModel = {
  generatedAt: string;
  pageTitle: string;
  pageDescription: string;
  moduleLabel: string;
  moduleNote: string;
  moduleStatus: string;
  moduleLoading: boolean;
  newsMode: string;
  newsModeLabel: string;
  newsModeOptions: Array<{
    value: string;
    label: string;
  }>;
  upstreamServiceStatus: NewsUpstreamServiceStatus;
  channelSummaries: NewsChannelSummary[];
  rankedHeadlines: NewsHeadlineView[];
};
