import type { StockMarketAllRefreshPayload } from "../model/market-data.types";

/**
 * 请求取消指定的全部标的刷新任务。
 * @param jobId 全部标的刷新任务 ID。
 * @returns 后端更新后的任务状态。
 */
export async function cancelStockMarketAllRefresh(jobId: string): Promise<StockMarketAllRefreshPayload> {
  const response = await fetch(`/api/frontend/modules/market-data/stocks/refresh-all/${jobId}/cancel`, {
    headers: {
      Accept: "application/json",
    },
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`stock all refresh cancel failed: ${response.status}`);
  }
  return (await response.json()) as StockMarketAllRefreshPayload;
}
