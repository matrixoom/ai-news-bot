import { useQuery } from "@tanstack/react-query";
import { getStockMarketInstruments } from "../api/get-stock-market-instruments";

/**
 * 读取股票市场标的列表。
 */
export function useStockMarketInstrumentsQuery(filters: {
  query: string;
  instrumentType: string;
  marketBoard: string;
}) {
  return useQuery({
    queryKey: ["stock-market-instruments", filters.query, filters.instrumentType, filters.marketBoard],
    queryFn: ({ signal }) =>
      getStockMarketInstruments({
        query: filters.query,
        instrumentType: filters.instrumentType,
        marketBoard: filters.marketBoard,
        signal,
      }),
  });
}
