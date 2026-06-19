import type { StockMarketAllRefreshPayload } from "../model/market-data.types";

/**
 * 读取最近一次全部标的刷新任务，手动刷新和 15:30 定时刷新共用同一进度。
 * @param options.signal 请求取消信号。
 * @returns 最近任务状态；尚未触发时 `job` 为 null。
 */
export async function getStockMarketAllRefresh(options: {
  signal?: AbortSignal;
} = {}): Promise<StockMarketAllRefreshPayload> {
  const response = await fetch("/api/frontend/modules/market-data/stocks/refresh-all/latest", {
    headers: { Accept: "application/json" },
    signal: options.signal,
  });
  if (!response.ok) {
    throw new Error(`stock all refresh status failed: ${response.status}`);
  }
  return (await response.json()) as StockMarketAllRefreshPayload;
}
