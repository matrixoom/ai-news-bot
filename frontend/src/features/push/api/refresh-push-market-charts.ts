import { toPushConfigRaw } from "../model/push-module-adapter";
import type {
  PushConfig,
  PushMarketChartRefreshResponseRaw,
} from "../model/push-module.types";

/**
 * 启动 Push preview 宽基指数三个月历史重建任务。
 */
export async function startPushMarketChartRefresh(
  config: PushConfig,
): Promise<PushMarketChartRefreshResponseRaw> {
  const response = await fetch("/api/push/market-chart-refresh", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ config: toPushConfigRaw(config) }),
  });

  return readRefreshResponse(response, "push market chart refresh start failed");
}

/**
 * 查询宽基指数历史重建任务进度。
 */
export async function getPushMarketChartRefresh(
  jobId: string,
): Promise<PushMarketChartRefreshResponseRaw> {
  const response = await fetch(`/api/push/market-chart-refresh/${encodeURIComponent(jobId)}`, {
    headers: {
      Accept: "application/json",
    },
  });

  return readRefreshResponse(response, "push market chart refresh status failed");
}

async function readRefreshResponse(
  response: Response,
  fallbackMessage: string,
): Promise<PushMarketChartRefreshResponseRaw> {
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `${fallbackMessage}: ${response.status}`);
  }
  return payload as PushMarketChartRefreshResponseRaw;
}
