import type { StockMarketOverviewPayload } from "../model/market-data.types";

/**
 * 读取股票市场指数与涨跌家数摘要。
 * @param signal 请求取消信号。
 * @returns 股票市场概览数据。
 */
export async function getStockMarketOverview(signal?: AbortSignal): Promise<StockMarketOverviewPayload> {
  const response = await fetch("/api/frontend/modules/market-data/stocks/overview", {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    throw new Error(`stock market overview request failed: ${response.status}`);
  }
  return (await response.json()) as StockMarketOverviewPayload;
}
