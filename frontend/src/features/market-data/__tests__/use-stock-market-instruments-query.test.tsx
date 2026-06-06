import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { useStockMarketInstrumentsQuery } from "../hooks/use-stock-market-instruments-query";
import type { StockInstrumentListPayload } from "../model/market-data.types";

const mocks = vi.hoisted(() => ({
  getStockMarketInstruments: vi.fn(),
}));

vi.mock("../api/get-stock-market-instruments", () => ({
  getStockMarketInstruments: mocks.getStockMarketInstruments,
}));

/** 创建可由测试主动完成的异步请求。 */
function createDeferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve;
  });
  return { promise, resolve };
}

/** 构造股票分页接口测试数据。 */
function createPayload(symbol: string, offset: number): StockInstrumentListPayload {
  return {
    generated_at: "2026-06-06T00:00:00Z",
    items: [
      {
        symbol,
        code: symbol.slice(0, 6),
        exchange: "SZ",
        name: `测试股票${symbol.slice(0, 6)}`,
        instrument_type: "stock",
        market_board: "深市主板",
        listing_status: "listed",
        updated_at: "2026-06-06T00:00:00Z",
      },
    ],
    total: 6931,
    limit: 10,
    offset,
    universe_count: 6931,
    warning_message: "",
  };
}

/** 渲染真实查询 hook，便于观察首次访问新页时的数据状态。 */
function QueryHarness() {
  const [page, setPage] = useState(1);
  const query = useStockMarketInstrumentsQuery({
    query: "",
    instrumentType: "all",
    marketBoard: "all",
    listingStatus: "all",
    page,
    pageSize: 10,
  });

  return (
    <div>
      <button onClick={() => setPage(2)} type="button">下一页</button>
      <span data-testid="query-pending">{String(query.isPending)}</span>
      <span data-testid="query-placeholder">{String(query.isPlaceholderData)}</span>
      <span data-testid="query-total">{query.data?.total ?? 0}</span>
      <span data-testid="query-symbol">{query.data?.items[0]?.symbol ?? "无数据"}</span>
    </div>
  );
}

describe("useStockMarketInstrumentsQuery", () => {
  it("keeps the previous page visible while the first request for a new page is loading", async () => {
    const secondPageRequest = createDeferred<StockInstrumentListPayload>();
    mocks.getStockMarketInstruments.mockImplementation(({ page }: { page: number }) =>
      page === 1 ? Promise.resolve(createPayload("000001.SZ", 0)) : secondPageRequest.promise,
    );
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const user = userEvent.setup();

    render(
      <QueryClientProvider client={queryClient}>
        <QueryHarness />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("000001.SZ")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "下一页" }));

    expect(screen.getByTestId("query-pending")).toHaveTextContent("false");
    expect(screen.getByTestId("query-placeholder")).toHaveTextContent("true");
    expect(screen.getByTestId("query-total")).toHaveTextContent("6931");
    expect(screen.getByTestId("query-symbol")).toHaveTextContent("000001.SZ");

    secondPageRequest.resolve(createPayload("000011.SZ", 10));

    await waitFor(() => {
      expect(screen.getByTestId("query-placeholder")).toHaveTextContent("false");
      expect(screen.getByTestId("query-symbol")).toHaveTextContent("000011.SZ");
    });
  });
});
