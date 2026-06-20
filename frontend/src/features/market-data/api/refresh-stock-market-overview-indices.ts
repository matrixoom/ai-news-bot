import type { MarketDataRangeSelection, StockMarketOverviewPayload } from "../model/market-data.types";

export type StockMarketOverviewIndicesRefreshPayload = {
  ok: boolean;
  range: {
    type: string;
    start_date: string;
    end_date: string;
  };
  overview: StockMarketOverviewPayload;
};

/**
 * 按当前宽基 K 线时间跨度刷新指数历史。
 * @param range 前端当前选择的宽基 K 线时间范围。
 * @returns 后端刷新后的概览 payload。
 */
export async function refreshStockMarketOverviewIndices(
  range: MarketDataRangeSelection,
): Promise<StockMarketOverviewIndicesRefreshPayload> {
  const response = await fetch("/api/frontend/modules/market-data/stocks/overview/indices/refresh", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      range: range.type,
      start_date: range.startDate,
      end_date: range.endDate,
    }),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `stock market overview indices refresh failed: ${response.status}`);
  }
  return payload as StockMarketOverviewIndicesRefreshPayload;
}
