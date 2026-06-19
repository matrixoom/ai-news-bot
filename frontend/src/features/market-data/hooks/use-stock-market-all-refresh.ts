import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getStockMarketAllRefresh } from "../api/get-stock-market-all-refresh";
import { startStockMarketAllRefresh } from "../api/start-stock-market-all-refresh";
import type { StockMarketAllRefreshJob } from "../model/market-data.types";

const TERMINAL_STATUSES = new Set(["completed", "completed_with_warnings", "failed", "skipped"]);

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
      return job && isStockMarketAllRefreshRunning(job) ? 1000 : 15000;
    },
  });
  const mutation = useMutation({
    mutationFn: startStockMarketAllRefresh,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stock-market-all-refresh", "latest"] });
      queryClient.invalidateQueries({ queryKey: ["stock-market-instruments"] });
    },
  });

  return {
    isStarting: mutation.isPending,
    job: mutation.data?.job ?? latestQuery.data?.job ?? null,
    start: () => mutation.mutate(),
  };
}

/**
 * 判断任务是否还需要继续轮询。
 * @param job 后端返回的全标的刷新任务。
 * @returns 任务处于 pending 或 running 时返回 true。
 */
function isStockMarketAllRefreshRunning(job: StockMarketAllRefreshJob): boolean {
  return !TERMINAL_STATUSES.has(job.status);
}
