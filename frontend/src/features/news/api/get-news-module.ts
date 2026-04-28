import type { NewsModuleRawPayload } from "../model/news-module.types";

export async function getNewsModule(signal?: AbortSignal, newsMode?: string): Promise<NewsModuleRawPayload> {
  const query = new URLSearchParams();
  if (newsMode && newsMode !== "hybrid") {
    query.set("news_mode", newsMode);
  }

  const response = await fetch(`/api/frontend/dashboard${query.toString() ? `?${query.toString()}` : ""}`, {
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new Error(`news request failed: ${response.status}`);
  }

  return normalizeNewsPayload(await response.json());
}

/**
 * 将 Dashboard 聚合 payload 转为 News 页面沿用的视图 payload。
 * 参数 rawPayload 表示后端返回的聚合数据或旧模块数据。
 * 返回 News 模块页面可直接消费的稳定结构。
 */
function normalizeNewsPayload(rawPayload: unknown): NewsModuleRawPayload {
  const payload = rawPayload as NewsModuleRawPayload & {
    news_sections?: Array<NewsModuleRawPayload["module"]["details"][number]["section"]>;
  };

  if (payload.module?.id === "news") {
    return payload;
  }

  const sections = payload.news_sections ?? [];

  return {
    generated_at: payload.generated_at,
    news_mode: payload.news_mode,
    news_mode_options: payload.news_mode_options,
    upstream_service_status: payload.upstream_service_status,
    module: {
      id: "news",
      label: "新闻情报",
      note: `${sections.length} 个频道`,
      description: "科技、财经、政策新闻",
      status: sections.some((section) => section.status === "live") ? "live" : (sections[0]?.status ?? "compatible"),
      loading: false,
      details: sections.map((section) => ({
        id: section.key,
        label: section.title,
        kind: "news",
        note: `${section.item_count} 条`,
        section,
      })),
    },
  };
}
