import { toPushConfigRaw } from "../model/push-module-adapter";
import type { PushConfig, PushPreviewResponseRaw } from "../model/push-module.types";

/** 按当前草稿重绘预览；可选择是否先刷新外部数据。 */
export async function previewPush(
  config: PushConfig,
  options: { refreshData?: boolean } = {},
): Promise<PushPreviewResponseRaw> {
  const response = await fetch("/api/push/preview", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      config: toPushConfigRaw(config),
      refresh_data: options.refreshData ?? true,
    }),
  });

  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.error || `push preview failed: ${response.status}`);
  }

  return payload as PushPreviewResponseRaw;
}
