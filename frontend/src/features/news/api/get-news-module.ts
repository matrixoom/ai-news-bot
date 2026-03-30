import type { NewsModuleRawPayload } from "../model/news-module.types";

export async function getNewsModule(signal?: AbortSignal): Promise<NewsModuleRawPayload> {
  const response = await fetch("/api/frontend/modules/news", {
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new Error(`news request failed: ${response.status}`);
  }

  return (await response.json()) as NewsModuleRawPayload;
}
