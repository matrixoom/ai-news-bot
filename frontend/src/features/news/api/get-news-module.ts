import type { NewsModuleRawPayload } from "../model/news-module.types";

export async function getNewsModule(signal?: AbortSignal, newsMode?: string): Promise<NewsModuleRawPayload> {
  const query = new URLSearchParams();
  if (newsMode && newsMode !== "hybrid") {
    query.set("news_mode", newsMode);
  }

  const response = await fetch(`/api/frontend/modules/news${query.toString() ? `?${query.toString()}` : ""}`, {
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new Error(`news request failed: ${response.status}`);
  }

  return (await response.json()) as NewsModuleRawPayload;
}
