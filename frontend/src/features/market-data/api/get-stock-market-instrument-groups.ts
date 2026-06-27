import type { StockInstrumentGroupPayload } from "../model/market-data.types";

/**
 * 读取股票市场自定义标的分组。
 * @param options fetch 取消信号。
 * @returns 后端本地库中的分组列表。
 */
export async function getStockMarketInstrumentGroups(options: {
  signal?: AbortSignal;
} = {}): Promise<StockInstrumentGroupPayload> {
  const response = await fetch("/api/frontend/modules/market-data/stocks/groups", {
    headers: { Accept: "application/json" },
    signal: options.signal,
  });
  if (!response.ok) {
    throw new Error(`stock instrument groups load failed: ${response.status}`);
  }
  return (await response.json()) as StockInstrumentGroupPayload;
}
