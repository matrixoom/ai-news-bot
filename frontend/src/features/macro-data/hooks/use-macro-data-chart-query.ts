import { useQuery } from "@tanstack/react-query";
import { getMacroDataChart } from "../api/get-macro-data-chart";
import type { MacroDataFrequency, MacroDataRangeSelection } from "../model/macro-data.types";

export function useMacroDataChartQuery(chartId: string, range: MacroDataRangeSelection, frequency: MacroDataFrequency) {
  return useQuery({
    queryKey: ["macro-data-chart", chartId, range.type, range.startDate ?? "", range.endDate ?? "", frequency],
    queryFn: ({ signal }) => getMacroDataChart({ chartId, frequency, range, signal }),
  });
}
