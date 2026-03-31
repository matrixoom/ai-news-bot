import { toPushConfigRaw } from "../model/push-module-adapter";
import type { PushConfig, TriggerPushResponseRaw } from "../model/push-module.types";

export async function triggerPush(config: PushConfig): Promise<TriggerPushResponseRaw> {
  const response = await fetch("/api/push/trigger", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ config: toPushConfigRaw(config) }),
  });

  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.error || `push trigger failed: ${response.status}`);
  }

  return payload as TriggerPushResponseRaw;
}
