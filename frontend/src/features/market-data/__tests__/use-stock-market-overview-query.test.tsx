import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useStockMarketOverviewQuery } from "../hooks/use-stock-market-overview-query";

const mocks = vi.hoisted(() => ({
  getStockMarketOverview: vi.fn(),
}));

vi.mock("../api/get-stock-market-overview", () => ({
  getStockMarketOverview: mocks.getStockMarketOverview,
}));

function QueryHarness() {
  const query = useStockMarketOverviewQuery();
  return <span>{query.data?.indices[0]?.display_name ?? "加载中"}</span>;
}

describe("useStockMarketOverviewQuery", () => {
  it("loads the stable overview contract through React Query", async () => {
    mocks.getStockMarketOverview.mockResolvedValue({
      generated_at: "2026-06-10T10:32:00Z",
      indices: [
        {
          symbol: "SSE",
          display_name: "上证指数",
          close: 3242.18,
          change: 42.18,
          change_pct: 1.32,
          trade_date: "2026-06-09",
          status: "live",
        },
      ],
      breadth: {
        trade_date: "2026-06-09",
        advanced: 1,
        declined: 1,
        unchanged: 0,
        total: 2,
        status: "live",
      },
    });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <QueryHarness />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("上证指数")).toBeInTheDocument();
    expect(mocks.getStockMarketOverview).toHaveBeenCalledOnce();
  });
});
