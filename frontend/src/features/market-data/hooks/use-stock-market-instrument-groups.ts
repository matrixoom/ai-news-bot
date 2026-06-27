import { useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getStockMarketInstrumentGroups } from "../api/get-stock-market-instrument-groups";
import { saveStockMarketInstrumentGroups } from "../api/save-stock-market-instrument-groups";
import type { StockInstrumentGroup } from "../model/market-data.types";

const STOCK_MARKET_INSTRUMENT_GROUPS_QUERY_KEY = ["stock-market-instrument-groups"] as const;
const EMPTY_STOCK_GROUPS: StockInstrumentGroup[] = [];

/**
 * 管理股票市场自定义标的分组的读取和保存。
 * @returns 分组列表、加载状态和保存函数。
 */
export function useStockMarketInstrumentGroups() {
  const queryClient = useQueryClient();
  const groupsQuery = useQuery({
    queryKey: STOCK_MARKET_INSTRUMENT_GROUPS_QUERY_KEY,
    queryFn: ({ signal }) => getStockMarketInstrumentGroups({ signal }),
  });
  const saveMutation = useMutation({
    mutationFn: saveStockMarketInstrumentGroups,
    onSuccess: (payload) => {
      queryClient.setQueryData(STOCK_MARKET_INSTRUMENT_GROUPS_QUERY_KEY, payload);
    },
  });
  const save = useCallback((groups: StockInstrumentGroup[]) => saveMutation.mutate(groups), [saveMutation]);

  return {
    errorMessage: groupsQuery.error
      ? normalizeGroupError(groupsQuery.error)
      : saveMutation.error
        ? normalizeGroupError(saveMutation.error)
        : "",
    groups: groupsQuery.data?.groups ?? EMPTY_STOCK_GROUPS,
    isPending: groupsQuery.isPending,
    isSaving: saveMutation.isPending,
    save,
  };
}

/**
 * 将分组接口错误压缩成短消息，避免界面暴露异常对象。
 * @param error 捕获到的异常对象。
 * @returns 可展示错误信息。
 */
function normalizeGroupError(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return "unknown stock instrument group error";
}
