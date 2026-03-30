import type {
  NewsModuleRawPayload,
  NewsModuleViewModel,
  NewsUpstreamServiceStatus,
  NewsUpstreamServiceStatusRaw,
} from "./news-module.types";

export function adaptNewsModule(response: NewsModuleRawPayload): NewsModuleViewModel {
  const channelSummaries = response.module.details.map((detail) => {
    const firstHeadline = detail.section.items[0];

    return {
      id: detail.section.key,
      title: detail.section.title,
      status: detail.section.status,
      description: detail.section.description,
      itemCount: detail.section.item_count,
      note: detail.note,
      topHeadline: firstHeadline?.title ?? "",
    };
  });

  const rankedHeadlines = response.module.details
    .flatMap((detail, channelIndex) =>
      detail.section.items.map((item, itemIndex) => ({
        rank: item.rank || itemIndex + 1,
        title: item.title,
        source: item.source,
        url: item.url,
        publishedAt: item.published_at,
        tag: item.tag,
        summary: item.summary,
        channelId: detail.section.key,
        channelTitle: detail.section.title,
        channelIndex,
      })),
    )
    .sort((left, right) => left.channelIndex - right.channelIndex || left.rank - right.rank)
    .map(({ channelIndex: _channelIndex, ...headline }) => headline);

  return {
    generatedAt: response.generated_at,
    pageTitle: "News",
    pageDescription: response.module.description,
    moduleLabel: response.module.label,
    moduleNote: response.module.note,
    moduleStatus: response.module.status,
    moduleLoading: response.module.loading,
    newsMode: response.news_mode,
    newsModeLabel:
      response.news_mode_options.find((option) => option.value === response.news_mode)?.label ?? response.news_mode,
    newsModeOptions: response.news_mode_options,
    upstreamServiceStatus: adaptUpstreamServiceStatus(response.upstream_service_status),
    channelSummaries,
    rankedHeadlines,
  };
}

function adaptUpstreamServiceStatus(status: NewsUpstreamServiceStatusRaw): NewsUpstreamServiceStatus {
  return {
    status: status.status,
    healthy: status.healthy,
    managed: status.managed,
    isLocal: status.is_local,
    baseUrl: status.base_url,
    detail: status.detail,
    summaryLabel: buildUpstreamSummaryLabel(status),
  };
}

function buildUpstreamSummaryLabel(status: NewsUpstreamServiceStatusRaw): string {
  const state = status.status.trim() || "unknown";

  if (status.healthy) {
    return `${state} · healthy`;
  }

  if (status.managed) {
    return `${state} · managed`;
  }

  return state;
}
