import { useQuery } from "@tanstack/react-query";
import { getMarketDataChart } from "../api/get-market-data-chart";
import type { MarketDataFrequency, MarketDataRangeSelection } from "../model/market-data.types";

export function useMarketDataChartQuery(
  chartId: string,
  range: MarketDataRangeSelection,
  frequency: MarketDataFrequency,
) {
  return useQuery({
    queryKey: ["market-data-chart", chartId, range.type, range.startDate ?? "", range.endDate ?? "", frequency],
    queryFn: ({ signal }) => getMarketDataChart({ chartId, frequency, range, signal }),
  });
}
