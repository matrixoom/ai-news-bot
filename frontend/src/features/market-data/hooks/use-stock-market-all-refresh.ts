import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cancelStockMarketAllRefresh } from "../api/cancel-stock-market-all-refresh";
import { getStockMarketAllRefresh } from "../api/get-stock-market-all-refresh";
import { startStockMarketAllRefresh } from "../api/start-stock-market-all-refresh";
import type {
  StockMarketAllRefreshJob,
  StockMarketAllRefreshMode,
  StockMarketAllRefreshOptions,
} from "../model/market-data.types";

const TERMINAL_STATUSES = new Set(["completed", "completed_with_warnings", "failed", "skipped", "canceled"]);

/**
 * 管理全部标的刷新任务的启动和轮询。
 * @returns 前端列表头部需要的任务状态、启动函数和提交中状态。
 */
export function useStockMarketAllRefresh() {
  const queryClient = useQueryClient();
  const latestQuery = useQuery({
    queryKey: ["stock-market-all-refresh", "latest"],
    queryFn: ({ signal }) => getStockMarketAllRefresh({ signal }),
    refetchInterval: (query) => {
      const job = query.state.data?.job;
      return job && isStockMarketAllRefreshRunning(job) ? 5000 : 15000;
    },
  });
  const mutation = useMutation({
    mutationFn: (payload: { mode: StockMarketAllRefreshMode; options?: StockMarketAllRefreshOptions }) =>
      startStockMarketAllRefresh(payload.mode, payload.options),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stock-market-all-refresh", "latest"] });
    },
  });
  const cancelMutation = useMutation({
    mutationFn: cancelStockMarketAllRefresh,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stock-market-all-refresh", "latest"] });
    },
  });

  return {
    cancel: (jobId: string) => cancelMutation.mutate(jobId),
    errorMessage: mutation.error
      ? normalizeRefreshError(mutation.error)
      : cancelMutation.error
        ? normalizeRefreshError(cancelMutation.error)
        : "",
    isCanceling: cancelMutation.isPending,
    isStarting: mutation.isPending,
    job: cancelMutation.data?.job ?? mutation.data?.job ?? latestQuery.data?.job ?? null,
    start: (mode: StockMarketAllRefreshMode, options?: StockMarketAllRefreshOptions) =>
      mutation.mutate({ mode, options }),
  };
}

/**
 * 将刷新启动异常压缩成可展示的短错误文案。
 * @param error mutation 捕获的异常对象。
 * @returns 可直接展示给用户的错误信息。
 */
function normalizeRefreshError(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return "unknown stock all refresh error";
}

/**
 * 判断任务是否还需要继续轮询。
 * @param job 后端返回的全标的刷新任务。
 * @returns 任务处于 pending 或 running 时返回 true。
 */
function isStockMarketAllRefreshRunning(job: StockMarketAllRefreshJob): boolean {
  return !TERMINAL_STATUSES.has(job.status);
}
