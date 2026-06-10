import { useQuery } from "@tanstack/react-query";
import { getStockMarketOverview } from "../api/get-stock-market-overview";

/** 读取股票市场概览，并按研究工作台的短周期自动刷新。 */
export function useStockMarketOverviewQuery() {
  return useQuery({
    queryKey: ["stock-market-overview"],
    queryFn: ({ signal }) => getStockMarketOverview(signal),
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,
  });
}
