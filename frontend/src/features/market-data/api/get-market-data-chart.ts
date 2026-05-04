import type { MarketChartPayload, MarketDataFrequency, MarketDataRangeSelection } from "../model/market-data.types";

export async function getMarketDataChart(options: {
  chartId: string;
  range: MarketDataRangeSelection;
  frequency: MarketDataFrequency;
  signal?: AbortSignal;
}): Promise<MarketChartPayload> {
  const params = new URLSearchParams({ frequency: options.frequency, range: options.range.type });
  if (options.range.type === "custom") {
    if (options.range.startDate) {
      params.set("start_date", options.range.startDate);
    }
    if (options.range.endDate) {
      params.set("end_date", options.range.endDate);
    }
  }
  const response = await fetch(`/api/frontend/modules/market-data/charts/${options.chartId}?${params.toString()}`, {
    headers: { Accept: "application/json" },
    signal: options.signal,
  });

  if (!response.ok) {
    throw new Error(`market data chart request failed: ${response.status}`);
  }

  return (await response.json()) as MarketChartPayload;
}
