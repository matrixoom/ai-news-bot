import { useQuery } from "@tanstack/react-query";
import { getRealEstateChart } from "../api/get-real-estate-chart";
import type { MarketDataFrequency, MarketDataRangeSelection } from "../model/market-data.types";

export function useRealEstateChartQuery(
  chartId: string,
  range: MarketDataRangeSelection,
  frequency: MarketDataFrequency,
  cities: string[],
) {
  return useQuery({
    queryKey: ["real-estate-chart", chartId, range.type, range.startDate ?? "", range.endDate ?? "", frequency, cities.join(",")],
    queryFn: ({ signal }) => getRealEstateChart({ chartId, frequency, range, cities, signal }),
    enabled: cities.length > 0,
  });
}
