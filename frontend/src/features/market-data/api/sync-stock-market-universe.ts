/**
 * 手动刷新 A 股和 ETF 标的列表。
 * @returns 标的同步结果。
 */
export async function syncStockMarketUniverse(): Promise<{ ok: boolean; counts: Record<string, number> }> {
  const response = await fetch("/api/frontend/modules/market-data/stocks/sync-universe", {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`stock universe sync failed: ${response.status}`);
  }
  return response.json() as Promise<{ ok: boolean; counts: Record<string, number> }>;
}
