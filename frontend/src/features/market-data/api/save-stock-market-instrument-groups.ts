import type { StockInstrumentGroup, StockInstrumentGroupPayload } from "../model/market-data.types";

/**
 * 整体保存股票市场自定义标的分组。
 * @param groups 需要写入本地数据库的分组列表。
 * @returns 后端规范化后的分组列表。
 */
export async function saveStockMarketInstrumentGroups(
  groups: StockInstrumentGroup[],
): Promise<StockInstrumentGroupPayload> {
  const response = await fetch("/api/frontend/modules/market-data/stocks/groups", {
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    method: "PUT",
    body: JSON.stringify({
      groups: groups.map((group) => ({
        id: group.id,
        name: group.name,
        symbols: group.symbols,
      })),
    }),
  });
  if (!response.ok) {
    throw new Error(`stock instrument groups save failed: ${response.status}`);
  }
  return (await response.json()) as StockInstrumentGroupPayload;
}
