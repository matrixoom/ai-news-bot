import { toPushConfigRaw } from "../model/push-module-adapter";
import type { PushConfig, PushModuleRawPayload } from "../model/push-module.types";

export async function updatePushConfig(config: PushConfig): Promise<PushModuleRawPayload> {
  const response = await fetch("/api/push/config", {
    method: "PUT",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ config: toPushConfigRaw(config) }),
  });

  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.error || `push config update failed: ${response.status}`);
  }

  return payload as PushModuleRawPayload;
}
