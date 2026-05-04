import type { MarketDataModulePayload, MarketDataTab } from "../model/market-data.types";

export async function getMarketDataModule(options: {
  tab: MarketDataTab;
  signal?: AbortSignal;
}): Promise<MarketDataModulePayload> {
  const params = new URLSearchParams({ tab: options.tab });
  const response = await fetch(`/api/frontend/modules/market-data?${params.toString()}`, {
    headers: { Accept: "application/json" },
    signal: options.signal,
  });

  if (!response.ok) {
    throw new Error(`market data module request failed: ${response.status}`);
  }

  return (await response.json()) as MarketDataModulePayload;
}
