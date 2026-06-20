import type { StockMarketAllRefreshPayload } from "../model/market-data.types";

/**
 * 启动全部标的近一年行情和公司概况后台刷新，已覆盖窗口的标的由后端跳过外部请求。
 * @returns 后端创建或复用的刷新任务状态。
 */
export async function startStockMarketAllRefresh(): Promise<StockMarketAllRefreshPayload> {
  const response = await fetch("/api/frontend/modules/market-data/stocks/refresh-all", {
    headers: { Accept: "application/json" },
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`stock all refresh start failed: ${response.status}`);
  }
  return (await response.json()) as StockMarketAllRefreshPayload;
}
