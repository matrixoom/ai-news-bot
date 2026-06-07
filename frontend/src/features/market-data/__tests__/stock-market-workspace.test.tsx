import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect, useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { StockMarketWorkspace } from "../components/stock-market-workspace";
import type { StockInstrument } from "../model/market-data.types";

const mocks = vi.hoisted(() => ({
  detailRanges: [] as Array<Record<string, unknown>>,
  instrumentFilters: [] as Array<Record<string, unknown>>,
  refresh: vi.fn(),
  syncUniverse: vi.fn(),
}));

const instruments: StockInstrument[] = Array.from({ length: 25 }, (_, index) => {
  const code = String(index + 1).padStart(6, "0");
  return {
    symbol: `${code}.SZ`,
    code,
    exchange: "SZ",
    name: index === 0 ? "平安银行" : `测试股票${index + 1}`,
    instrument_type: index === 20 ? "etf" : "stock",
    market_board: index === 20 ? "ETF" : "深市主板",
    listing_status: "listed",
    updated_at: "2026-06-06T00:00:00Z",
    latest_price: 10 + index,
  };
});

vi.mock("echarts", () => ({
  init: vi.fn(() => ({
    setOption: vi.fn(),
    dispose: vi.fn(),
  })),
}));

vi.mock("../hooks/use-stock-market-instruments-query", () => ({
  useStockMarketInstrumentsQuery: (filters: {
    query: string;
    instrumentType: string;
    marketBoard: string;
    listingStatus: string;
    page?: number;
    pageSize?: number;
  }) => {
    mocks.instrumentFilters.push(filters);
    const [resolvedRequest, setResolvedRequest] = useState(() => JSON.stringify(filters));
    const currentRequest = JSON.stringify(filters);
    const isPending = resolvedRequest !== currentRequest;

    useEffect(() => {
      if (!isPending) return;
      const timer = window.setTimeout(() => setResolvedRequest(currentRequest), 0);
      return () => window.clearTimeout(timer);
    }, [currentRequest, isPending]);

    const page = filters.page ?? 1;
    const pageSize = filters.pageSize ?? 10;
    const filtered = instruments.filter((instrument) => {
      const matchesQuery =
        !filters.query ||
        instrument.symbol.includes(filters.query) ||
        instrument.name.includes(filters.query);
      const matchesType =
        filters.instrumentType === "all" ||
        instrument.instrument_type === filters.instrumentType;
      const matchesBoard =
        filters.marketBoard === "all" ||
        instrument.market_board === filters.marketBoard;
      return matchesQuery && matchesType && matchesBoard;
    });
    const offset = (page - 1) * pageSize;
    return {
      isPending,
      isError: false,
      data: isPending
        ? undefined
        : {
            items: filtered.slice(offset, offset + pageSize),
            total: filtered.length,
            limit: pageSize,
            offset,
            warning_message: "",
          },
    };
  },
}));

vi.mock("../hooks/use-stock-market-detail-query", () => ({
  useStockMarketDetailQuery: (symbol: string | null, range: Record<string, unknown>) => {
    mocks.detailRanges.push(range);
    return {
      isPending: false,
      isError: false,
      data: symbol
        ? {
            instrument: instruments.find((instrument) => instrument.symbol === symbol) ?? instruments[0],
            daily_bars: [],
            profile: {
              listing_date: "",
              sector: "",
              industry: "",
              region: "",
            },
            financials: { series: [] },
            sync_state: {
              warning_message: "",
              synced_at: "",
            },
          }
        : undefined,
    };
  },
}));

vi.mock("../hooks/use-stock-market-refresh-mutation", () => ({
  useStockMarketRefreshMutation: () => ({
    isPending: false,
    mutate: mocks.refresh,
  }),
}));

vi.mock("../hooks/use-stock-market-universe-sync-mutation", () => ({
  useStockMarketUniverseSyncMutation: () => ({
    isPending: false,
    mutate: mocks.syncUniverse,
  }),
}));

describe("StockMarketWorkspace", () => {
  beforeEach(() => {
    mocks.detailRanges.length = 0;
    mocks.instrumentFilters.length = 0;
    mocks.refresh.mockClear();
    mocks.syncUniverse.mockClear();
  });

  it("uses real pagination and supports previous and next page navigation", async () => {
    const user = userEvent.setup();
    render(<StockMarketWorkspace />);

    await user.click(screen.getByRole("button", { name: "第 2 页" }));
    expect(within(screen.getByRole("table")).getByText("000011.SZ")).toBeInTheDocument();
    expect(mocks.instrumentFilters.at(-1)).toMatchObject({ page: 2, pageSize: 10 });

    await user.click(screen.getByRole("button", { name: "下一页" }));
    expect(within(screen.getByRole("table")).getByText("000021.SZ")).toBeInTheDocument();
    expect(mocks.instrumentFilters.at(-1)).toMatchObject({ page: 3, pageSize: 10 });

    await user.click(screen.getByRole("button", { name: "上一页" }));
    expect(within(screen.getByRole("table")).getByText("000011.SZ")).toBeInTheDocument();
    expect(mocks.instrumentFilters.at(-1)).toMatchObject({ page: 2, pageSize: 10 });
  });

  it("applies search and dropdown filters and resets pagination", async () => {
    const user = userEvent.setup();
    render(<StockMarketWorkspace />);

    await user.click(screen.getByRole("button", { name: "第 2 页" }));
    await user.clear(screen.getByRole("searchbox"));
    await user.type(screen.getByRole("searchbox"), "000021");
    await user.selectOptions(screen.getByLabelText("证券类型"), "etf");
    await user.selectOptions(screen.getByLabelText("市场类型"), "ETF");

    await waitFor(() => {
      expect(mocks.instrumentFilters.at(-1)).toMatchObject({
        query: "000021",
        instrumentType: "etf",
        marketBoard: "ETF",
        page: 1,
        pageSize: 10,
      });
    });
  });

  it("collapses the stock list and removes the inner list scrollbar", async () => {
    const user = userEvent.setup();
    render(<StockMarketWorkspace />);

    expect(screen.getByTestId("instrument-list-body")).not.toHaveClass("overflow-auto");
    await user.click(screen.getByRole("button", { name: "折叠股票列表" }));

    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "展开股票列表" })).toHaveAttribute("aria-expanded", "false");
  });

  it("shows custom controls only for a custom range", async () => {
    const user = userEvent.setup();
    render(<StockMarketWorkspace />);

    expect(screen.queryByLabelText("起始日期")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "刷新数据" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "自定义" }));

    expect(screen.getByLabelText("起始日期")).toBeInTheDocument();
    expect(screen.getByLabelText("结束日期")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "刷新数据" })).toBeInTheDocument();
  });

  it("uses the latest month as the default stock range", () => {
    render(<StockMarketWorkspace />);

    expect(mocks.detailRanges.at(-1)).toMatchObject({ type: "1m" });
    expect(screen.getByRole("button", { name: "近1月" })).toHaveClass("bg-blue-50");
  });

  it("separates overview and financial content into real tabs", async () => {
    const user = userEvent.setup();
    render(<StockMarketWorkspace />);

    expect(screen.getByRole("tab", { name: "概览" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "财务数据" })).toHaveAttribute("aria-selected", "false");
    expect(screen.getByRole("button", { name: "近3月" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "财务数据" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "财务数据" }));

    expect(screen.getByRole("tab", { name: "财务数据" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("heading", { name: "财务数据" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "近3月" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "概览" }));

    expect(screen.getByRole("button", { name: "近3月" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "财务数据" })).not.toBeInTheDocument();
  });

  it("keeps the paginator at the bottom of the viewport-height list panel", () => {
    render(<StockMarketWorkspace />);

    const panel = screen.getByTestId("instrument-list-panel");
    const paginator = screen.getByLabelText("股票列表分页");

    expect(panel).toHaveClass("h-[calc(100vh-14.375rem)]");
    expect(within(panel).getByLabelText("股票列表分页")).toBe(paginator);
  });
});
