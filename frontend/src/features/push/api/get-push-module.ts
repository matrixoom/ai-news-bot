import type { PushModuleRawPayload } from "../model/push-module.types";

export async function getPushModule(options?: {
  signal?: AbortSignal;
  includePreview?: boolean;
  refresh?: boolean;
}): Promise<PushModuleRawPayload> {
  const params = new URLSearchParams();
  if (options?.includePreview === false) {
    params.set("include_preview", "0");
  }
  if (options?.refresh) {
    params.set("refresh", "1");
  }
  const path = params.size ? `/api/frontend/modules/push?${params.toString()}` : "/api/frontend/modules/push";
  const response = await fetch(path, {
    headers: { Accept: "application/json" },
    signal: options?.signal,
  });

  if (!response.ok) {
    throw new Error(`push request failed: ${response.status}`);
  }

  return (await response.json()) as PushModuleRawPayload;
}
