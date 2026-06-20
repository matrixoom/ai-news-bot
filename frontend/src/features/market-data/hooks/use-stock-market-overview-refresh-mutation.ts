import { useMutation, useQueryClient } from "@tanstack/react-query";
import { refreshStockMarketOverviewIndices } from "../api/refresh-stock-market-overview-indices";
import type { MarketDataRangeSelection } from "../model/market-data.types";

/** 刷新宽基指数历史，并让概览查询重新读取最新本地数据。 */
export function useStockMarketOverviewRefreshMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (range: MarketDataRangeSelection) => refreshStockMarketOverviewIndices(range),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stock-market-overview"] });
    },
  });
}
