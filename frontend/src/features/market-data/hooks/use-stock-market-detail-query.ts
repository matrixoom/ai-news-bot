import { useQuery } from "@tanstack/react-query";
import { getStockMarketDetail } from "../api/get-stock-market-detail";
import type {
  MarketDataRangeSelection,
  StockFinancialReportType,
} from "../model/market-data.types";

/**
 * 读取选中股票的日线、概况和财报详情。
 */
export function useStockMarketDetailQuery(
  symbol: string | null,
  range: MarketDataRangeSelection,
  financialReportType: StockFinancialReportType,
) {
  return useQuery({
    enabled: Boolean(symbol),
    queryKey: [
      "stock-market-detail",
      symbol,
      range.type,
      range.startDate ?? "",
      range.endDate ?? "",
      financialReportType,
    ],
    queryFn: ({ signal }) =>
      getStockMarketDetail({
        symbol: symbol ?? "",
        range,
        financialReportType,
        signal,
      }),
  });
}
