import { useQuery } from "@tanstack/react-query";
import { getStockMarketInstruments } from "../api/get-stock-market-instruments";

/**
 * 读取股票市场标的列表。
 */
export function useStockMarketInstrumentsQuery(filters: {
  query: string;
  instrumentType: string;
  marketBoard: string;
  listingStatus?: string;
  page: number;
  pageSize: number;
}) {
  return useQuery({
    queryKey: [
      "stock-market-instruments",
      filters.query,
      filters.instrumentType,
      filters.marketBoard,
      filters.listingStatus ?? "all",
      filters.page,
      filters.pageSize,
    ],
    queryFn: ({ signal }) =>
      getStockMarketInstruments({
        query: filters.query,
        instrumentType: filters.instrumentType,
        marketBoard: filters.marketBoard,
        listingStatus: filters.listingStatus ?? "all",
        page: filters.page,
        pageSize: filters.pageSize,
        signal,
      }),
  });
}
