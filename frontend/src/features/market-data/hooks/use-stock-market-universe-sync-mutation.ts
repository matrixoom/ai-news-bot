import { useMutation, useQueryClient } from "@tanstack/react-query";
import { syncStockMarketUniverse } from "../api/sync-stock-market-universe";

/**
 * 手动刷新 A 股/ETF 标的池。
 */
export function useStockMarketUniverseSyncMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: syncStockMarketUniverse,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stock-market-instruments"] });
    },
  });
}
