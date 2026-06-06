import type { StockInstrumentListPayload } from "../model/market-data.types";

/**
 * 读取股票市场标的列表，支持按代码、名称和类型筛选。
 * @param options.query 股票代码或名称关键字。
 * @param options.instrumentType 股票或 ETF 类型筛选。
 * @param options.marketBoard 市场板块筛选。
 * @param options.page 当前页码，从 1 开始。
 * @param options.pageSize 每页返回条数。
 * @param options.signal 请求取消信号。
 * @returns 股票/ETF 标的分页结果。
 */
export async function getStockMarketInstruments(options: {
  query: string;
  instrumentType: string;
  marketBoard: string;
  listingStatus?: string;
  page: number;
  pageSize: number;
  signal?: AbortSignal;
}): Promise<StockInstrumentListPayload> {
  const params = new URLSearchParams({
    query: options.query,
    instrument_type: options.instrumentType,
    market_board: options.marketBoard,
    listing_status: options.listingStatus ?? "all",
    limit: String(options.pageSize),
    offset: String((options.page - 1) * options.pageSize),
  });
  const response = await fetch(`/api/frontend/modules/market-data/stocks?${params.toString()}`, {
    headers: { Accept: "application/json" },
    signal: options.signal,
  });
  if (!response.ok) {
    throw new Error(`stock instrument request failed: ${response.status}`);
  }
  return (await response.json()) as StockInstrumentListPayload;
}
