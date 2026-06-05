import type {
  MarketDataRangeSelection,
  StockDetailPayload,
  StockFinancialReportType,
} from "../model/market-data.types";

/**
 * 读取选中股票的行情、概况和财报详情。
 * @param options.symbol 带交易所后缀的股票代码。
 * @param options.range 时间范围。
 * @param options.financialReportType 财报维度。
 * @param options.signal 请求取消信号。
 * @returns 股票详情 payload。
 */
export async function getStockMarketDetail(options: {
  symbol: string;
  range: MarketDataRangeSelection;
  financialReportType: StockFinancialReportType;
  signal?: AbortSignal;
}): Promise<StockDetailPayload> {
  const params = new URLSearchParams({
    range: options.range.type,
    financial_report_type: options.financialReportType,
  });
  if (options.range.type === "custom") {
    if (options.range.startDate) params.set("start_date", options.range.startDate);
    if (options.range.endDate) params.set("end_date", options.range.endDate);
  }
  const response = await fetch(
    `/api/frontend/modules/market-data/stocks/${options.symbol}?${params.toString()}`,
    {
      headers: { Accept: "application/json" },
      signal: options.signal,
    },
  );
  if (!response.ok) {
    throw new Error(`stock detail request failed: ${response.status}`);
  }
  return (await response.json()) as StockDetailPayload;
}
