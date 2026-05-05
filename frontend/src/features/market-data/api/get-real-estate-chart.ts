import type { MarketChartPayload, MarketDataFrequency, MarketDataRangeSelection } from "../model/market-data.types";

export async function getRealEstateChart(options: {
  chartId: string;
  range: MarketDataRangeSelection;
  frequency: MarketDataFrequency;
  cities: string[];
  signal?: AbortSignal;
}): Promise<MarketChartPayload> {
  const params = new URLSearchParams({
    frequency: options.frequency,
    range: options.range.type,
    cities: options.cities.join(","),
  });
  if (options.range.type === "custom") {
    if (options.range.startDate) {
      params.set("start_date", options.range.startDate);
    }
    if (options.range.endDate) {
      params.set("end_date", options.range.endDate);
    }
  }
  const response = await fetch(
    `/api/frontend/modules/market-data/charts/${options.chartId}?${params.toString()}`,
    {
      headers: { Accept: "application/json" },
      signal: options.signal,
    },
  );

  if (!response.ok) {
    throw new Error(`real estate chart request failed: ${response.status}`);
  }

  return (await response.json()) as MarketChartPayload;
}
