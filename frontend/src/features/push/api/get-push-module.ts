import type { PushModuleRawPayload } from "../model/push-module.types";

export async function getPushModule(signal?: AbortSignal): Promise<PushModuleRawPayload> {
  const response = await fetch("/api/frontend/modules/push", {
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new Error(`push request failed: ${response.status}`);
  }

  return (await response.json()) as PushModuleRawPayload;
}
