import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { getStockMarketDetail } from "../api/get-stock-market-detail";
import type {
  MarketDataRangeSelection,
  StockFinancialReportType,
  StockPriceAdjustment,
} from "../model/market-data.types";

/**
 * 读取选中股票的日线、概况和财报详情。
 */
export function useStockMarketDetailQuery(
  symbol: string | null,
  range: MarketDataRangeSelection,
  financialReportType: StockFinancialReportType,
  adjustType: StockPriceAdjustment,
  options: { recordAccess?: boolean; accessRequestId?: number } = {},
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
      adjustType,
      options.accessRequestId ?? 0,
    ],
    queryFn: ({ signal }) =>
      getStockMarketDetail({
        symbol: symbol ?? "",
        range,
        financialReportType,
        adjustType,
        recordAccess: options.recordAccess ?? true,
        signal,
      }),
    // 后台全标的刷新写库时详情接口可能变慢，保留上一份数据避免页面卡成空态。
    placeholderData: keepPreviousData,
  });
}
