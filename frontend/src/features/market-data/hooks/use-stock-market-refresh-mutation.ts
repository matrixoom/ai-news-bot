import { useMutation, useQueryClient } from "@tanstack/react-query";
import { refreshStockMarketDetail } from "../api/refresh-stock-market-detail";
import type {
  MarketDataRangeSelection,
  StockFinancialReportType,
} from "../model/market-data.types";

/**
 * 手动刷新选中股票的当前时间窗口。
 */
export function useStockMarketRefreshMutation(
  symbol: string | null,
  range: MarketDataRangeSelection,
  financialReportType: StockFinancialReportType,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => {
      if (!symbol) {
        throw new Error("stock symbol is required");
      }
      return refreshStockMarketDetail({ symbol, range, financialReportType });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stock-market-detail", symbol] });
    },
  });
}
