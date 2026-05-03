import { useMutation, useQueryClient } from "@tanstack/react-query";
import { refreshMacroDataChart } from "../api/refresh-macro-data-chart";

export function useMacroDataRefreshMutation(chartId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => refreshMacroDataChart(chartId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["macro-data-chart", chartId] });
    },
  });
}
