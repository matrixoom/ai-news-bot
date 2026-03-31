import { toPushConfigRaw } from "../model/push-module-adapter";
import type { PushConfig, PushPreviewResponseRaw } from "../model/push-module.types";

export async function previewPush(config: PushConfig): Promise<PushPreviewResponseRaw> {
  const response = await fetch("/api/push/preview", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ config: toPushConfigRaw(config) }),
  });

  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.error || `push preview failed: ${response.status}`);
  }

  return payload as PushPreviewResponseRaw;
}
