import type {
  StockMarketAllRefreshMode,
  StockMarketAllRefreshOptions,
  StockMarketAllRefreshPayload,
} from "../model/market-data.types";

/**
 * 启动全部标的后台刷新，已覆盖窗口的标的由后端跳过外部请求。
 * @param mode 刷新历史窗口或仅刷新当日行情。
 * @returns 后端创建或复用的刷新任务状态。
 */
export async function startStockMarketAllRefresh(
  mode: StockMarketAllRefreshMode = "history",
  options: StockMarketAllRefreshOptions = {},
): Promise<StockMarketAllRefreshPayload> {
  const response = await fetch("/api/frontend/modules/market-data/stocks/refresh-all", {
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    method: "POST",
    body: JSON.stringify({
      mode,
      groupName: options.groupName ?? "全部",
      ...(options.symbols ? { symbols: options.symbols } : {}),
    }),
  });
  if (!response.ok) {
    throw new Error(`stock all refresh start failed: ${response.status}`);
  }
  return (await response.json()) as StockMarketAllRefreshPayload;
}
