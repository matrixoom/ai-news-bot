import { useQuery } from "@tanstack/react-query";
import { getMacroDataChart } from "../api/get-macro-data-chart";
import type { MacroDataRangeSelection } from "../model/macro-data.types";

export function useMacroDataChartQuery(chartId: string, range: MacroDataRangeSelection) {
  return useQuery({
    queryKey: ["macro-data-chart", chartId, range.type, range.startDate ?? "", range.endDate ?? ""],
    queryFn: ({ signal }) => getMacroDataChart({ chartId, range, signal }),
  });
}
