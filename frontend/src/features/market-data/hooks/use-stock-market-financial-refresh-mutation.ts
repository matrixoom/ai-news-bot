import { useMutation, useQueryClient } from "@tanstack/react-query";
import { refreshStockMarketFinancials } from "../api/refresh-stock-market-financials";
import type {
  MarketDataRangeSelection,
  StockFinancialReportType,
} from "../model/market-data.types";

/**
 * 手动刷新选中股票的当前财务时间窗口。
 */
export function useStockMarketFinancialRefreshMutation(
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
      return refreshStockMarketFinancials({ symbol, range, financialReportType });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stock-market-detail", symbol] });
    },
  });
}
