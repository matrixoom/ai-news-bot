import { useMutation, useQueryClient } from "@tanstack/react-query";
import { refreshMarketDataChart } from "../api/refresh-market-data-chart";

export function useMarketDataRefreshMutation(chartId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => refreshMarketDataChart(chartId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["market-data-chart", chartId] });
    },
  });
}
