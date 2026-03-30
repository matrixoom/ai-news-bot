import type { MarketModuleRawPayload } from "../model/market-module.types";

export async function getMarketModule(signal?: AbortSignal): Promise<MarketModuleRawPayload> {
  const response = await fetch("/api/frontend/modules/market", {
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new Error(`market request failed: ${response.status}`);
  }

  return (await response.json()) as MarketModuleRawPayload;
}
