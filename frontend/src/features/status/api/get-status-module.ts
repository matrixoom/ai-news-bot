import type { StatusModuleRawPayload } from "../model/status-module.types";

export async function getStatusModule(signal?: AbortSignal, newsMode?: string): Promise<StatusModuleRawPayload> {
  const query = new URLSearchParams();
  if (newsMode && newsMode !== "hybrid") {
    query.set("news_mode", newsMode);
  }

  const response = await fetch(`/api/frontend/modules/status${query.toString() ? `?${query.toString()}` : ""}`, {
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new Error(`status request failed: ${response.status}`);
  }

  return (await response.json()) as StatusModuleRawPayload;
}
