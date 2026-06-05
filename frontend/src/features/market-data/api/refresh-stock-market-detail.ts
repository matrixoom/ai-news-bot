import type {
  MarketDataRangeSelection,
  StockDetailPayload,
  StockFinancialReportType,
} from "../model/market-data.types";

/**
 * 手动刷新选中股票在当前时间范围内的日线行情。
 * @param options.symbol 带交易所后缀的股票代码。
 * @param options.range 时间范围。
 * @param options.financialReportType 财报维度。
 * @returns 刷新后的股票详情 payload。
 */
export async function refreshStockMarketDetail(options: {
  symbol: string;
  range: MarketDataRangeSelection;
  financialReportType: StockFinancialReportType;
}): Promise<StockDetailPayload> {
  const response = await fetch(`/api/frontend/modules/market-data/stocks/${options.symbol}/sync`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      range: options.range.type,
      start_date: options.range.startDate,
      end_date: options.range.endDate,
      financial_report_type: options.financialReportType,
    }),
  });
  if (!response.ok) {
    throw new Error(`stock detail refresh failed: ${response.status}`);
  }
  return (await response.json()) as StockDetailPayload;
}
