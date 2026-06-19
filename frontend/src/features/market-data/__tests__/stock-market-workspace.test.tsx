import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect, useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { StockMarketWorkspace } from "../components/stock-market-workspace";
import type { StockInstrument } from "../model/market-data.types";

const mocks = vi.hoisted(() => ({
  detailRanges: [] as Array<Record<string, unknown>>,
  echartOptions: [] as Array<Record<string, unknown>>,
  instrumentFilters: [] as Array<Record<string, unknown>>,
  refresh: vi.fn(),
}));

const resizeObserverCallbacks: ResizeObserverCallback[] = [];

class ResizeObserverMock implements ResizeObserver {
  constructor(callback: ResizeObserverCallback) {
    resizeObserverCallbacks.push(callback);
  }

  disconnect() {}

  observe() {}

  unobserve() {}
}

const instruments: StockInstrument[] = Array.from({ length: 25 }, (_, index) => {
  const code = String(index + 1).padStart(6, "0");
  return {
    symbol: `${code}.SZ`,
    code,
    exchange: "SZ",
    name: index === 0 ? "平安银行" : index === 1 ? "名称较长的测试股票股份有限公司" : `测试股票${index + 1}`,
    instrument_type: index === 20 ? "etf" : "stock",
    market_board: index === 20 ? "ETF" : "深市主板",
    listing_status: "listed",
    updated_at: "2026-06-06T00:00:00Z",
    latest_price: 10 + index,
  };
});

const financialSeries = [
  {
    metric: "revenue",
    label: "营业收入",
    points: [
      { period: "2021-12-31", value: 100, unit: "亿元" },
      { period: "2025-12-31", value: 200, unit: "亿元" },
    ],
  },
  {
    metric: "cash_flow",
    label: "经营活动现金流",
    points: [
      { period: "2021-12-31", value: 20, unit: "亿元" },
      { period: "2025-12-31", value: 40, unit: "亿元" },
    ],
  },
  {
    metric: "roe",
    label: "ROE",
    points: [
      { period: "2021-12-31", value: 8.1, unit: "%" },
      { period: "2025-12-31", value: 9.2, unit: "%" },
    ],
  },
  {
    metric: "revenue_yoy",
    label: "营收同比",
    points: [
      { period: "2021-12-31", value: 5.1, unit: "%" },
      { period: "2025-12-31", value: 6.2, unit: "%" },
    ],
  },
  {
    metric: "net_profit_yoy",
    label: "净利润同比",
    points: [
      { period: "2021-12-31", value: 4.1, unit: "%" },
      { period: "2025-12-31", value: 5.2, unit: "%" },
    ],
  },
  {
    metric: "debt_asset_ratio",
    label: "资产负债率",
    points: [
      { period: "2021-12-31", value: 90.1, unit: "%" },
      { period: "2025-12-31", value: 89.2, unit: "%" },
    ],
  },
];

const dailyBars = [
  {
    date: "2026-06-05",
    open: 10,
    high: 11,
    low: 9,
    close: 10.5,
    volume: 1000,
    ma5: 10.2,
    ma10: 10.1,
    ma20: null,
    ma60: null,
    ma120: null,
    pe_ttm: 5.1,
    pb_mrq: 0.48,
    dividend_yield_ttm: 3.2,
    total_market_cap: 2130.77,
  },
  {
    date: "2026-06-06",
    open: 10.5,
    high: 11.5,
    low: 10,
    close: 11,
    volume: 1200,
    ma5: 10.4,
    ma10: 10.2,
    ma20: null,
    ma60: null,
    ma120: null,
    pe_ttm: null,
    pb_mrq: 0.49,
    dividend_yield_ttm: 3.1,
    total_market_cap: 2140.88,
  },
];

vi.mock("echarts", () => ({
  init: vi.fn(() => ({
    setOption: vi.fn((option: Record<string, unknown>) => mocks.echartOptions.push(option)),
    resize: vi.fn(),
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
            daily_bars: dailyBars,
            profile: {
              listing_date: "",
              sector: "",
              industry: "",
              region: "",
            },
            financials: { series: financialSeries },
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
  useStockMarketRefreshMutation: (
    symbol: string | null,
    range: Record<string, unknown>,
    financialReportType: string,
  ) => ({
    isPending: false,
    mutate: () => mocks.refresh({ symbol, range, financialReportType }),
  }),
}));

vi.mock("../hooks/use-stock-market-overview-query", () => ({
  useStockMarketOverviewQuery: () => ({
    isPending: false,
    isError: false,
    data: {
      generated_at: "2026-06-10T10:32:00Z",
      indices: [
        {
          symbol: "CSI300",
          display_name: "沪深 300",
          close: 3921.5,
          change: 21.5,
          change_pct: 0.55,
          trade_date: "2026-06-09",
          status: "live",
          daily_bars: [
            {
              date: "2026-04-01",
              open: 3850,
              high: 3860,
              low: 3840,
              close: 3850,
              volume: 800,
              ma5: null,
              ma10: null,
              ma20: null,
              ma60: null,
              ma120: null,
              pe_ttm: null,
              pb_mrq: null,
              dividend_yield_ttm: null,
              total_market_cap: null,
            },
            {
              date: "2026-06-05",
              open: 3900,
              high: 3900,
              low: 3900,
              close: 3900,
              volume: 1000,
              ma5: null,
              ma10: null,
              ma20: null,
              ma60: null,
              ma120: null,
              pe_ttm: null,
              pb_mrq: null,
              dividend_yield_ttm: null,
              total_market_cap: null,
            },
            {
              date: "2026-06-09",
              open: 3900,
              high: 3921.5,
              low: 3900,
              close: 3921.5,
              volume: 1200,
              ma5: null,
              ma10: null,
              ma20: null,
              ma60: null,
              ma120: null,
              pe_ttm: null,
              pb_mrq: null,
              dividend_yield_ttm: null,
              total_market_cap: null,
            },
          ],
        },
        {
          symbol: "CSI500",
          display_name: "中证 500",
          close: 6088,
          change: -12,
          change_pct: -0.2,
          trade_date: "2026-06-09",
          status: "live",
        },
        {
          symbol: "CSI1000",
          display_name: "中证 1000",
          close: 6740,
          change: 40,
          change_pct: 0.6,
          trade_date: "2026-06-09",
          status: "live",
        },
        {
          symbol: "SSE",
          display_name: "上证指数",
          close: 3242.18,
          change: 42.18,
          change_pct: 1.32,
          trade_date: "2026-06-09",
          status: "live",
        },
        {
          symbol: "SZSE",
          display_name: "深证成指",
          close: 10186.45,
          change: -18.2,
          change_pct: -0.18,
          trade_date: "2026-06-09",
          status: "live",
        },
        {
          symbol: "CHINEXT",
          display_name: "创业板指",
          close: 2112.6,
          change: 12.6,
          change_pct: 0.6,
          trade_date: "2026-06-09",
          status: "live",
        },
        {
          symbol: "HSTECH",
          display_name: "恒生科技指数",
          close: 4285,
          change: -15,
          change_pct: -0.35,
          trade_date: "2026-06-09",
          status: "live",
        },
      ],
      breadth: {
        trade_date: "2026-06-09",
        advanced: 3421,
        declined: 1428,
        unchanged: 82,
        total: 4931,
        status: "live",
      },
    },
  }),
}));

describe("StockMarketWorkspace", () => {
  beforeEach(() => {
    mocks.detailRanges.length = 0;
    mocks.echartOptions.length = 0;
    mocks.instrumentFilters.length = 0;
    mocks.refresh.mockClear();
    resizeObserverCallbacks.length = 0;
    vi.stubGlobal("ResizeObserver", ResizeObserverMock);
  });

  it("renders real market overview metrics with non-color direction labels", () => {
    render(<StockMarketWorkspace />);

    expect(screen.getByRole("region", { name: "市场概览" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "市场概览" })).toHaveClass("overflow-x-auto");
    expect(screen.getByRole("region", { name: "市场概览" })).toHaveStyle({
      gridTemplateColumns: "repeat(8, minmax(8rem, 1fr))",
    });
    expect(screen.getByText("沪深 300")).toBeInTheDocument();
    expect(screen.getByText("中证 500")).toBeInTheDocument();
    expect(screen.getByText("中证 1000")).toBeInTheDocument();
    expect(screen.getByText("上证指数")).toBeInTheDocument();
    expect(screen.getByText("创业板指")).toBeInTheDocument();
    expect(screen.getByText("恒生科技指数")).toBeInTheDocument();
    expect(screen.getByText("市场宽度")).toBeInTheDocument();
    expect(screen.getByText("↑ 3421")).toBeInTheDocument();
    expect(screen.getByText("↓ 1428")).toBeInTheDocument();
  });

  it("expands a broad index kline chart from the overview strip", async () => {
    const user = userEvent.setup();
    render(<StockMarketWorkspace />);

    await user.click(screen.getByRole("button", { name: /展开沪深 300宽基指数K线/ }));

    expect(screen.getByRole("region", { name: "沪深 300 宽基指数K线" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "CSI300 日级别行情K线" })).toBeInTheDocument();
    expect(screen.getByLabelText("宽基指数时间范围")).toBeInTheDocument();
    expect(screen.getByLabelText("沪深 300 当前时间跨度涨幅")).toHaveTextContent("区间涨幅 +0.55%");
    expect(screen.getByLabelText("沪深 300 当前时间跨度涨幅")).toHaveClass("text-ink");
    expect(within(screen.getByLabelText("沪深 300 当前时间跨度涨幅")).getByText("+0.55%")).toHaveClass("text-positive");
    expect(screen.queryByRole("searchbox")).not.toBeInTheDocument();
    expect(screen.queryByTestId("instrument-list-panel")).not.toBeInTheDocument();
    expect(screen.queryByTestId("stock-detail-panel")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /展开沪深 300宽基指数K线/ })).toHaveAttribute(
      "aria-expanded",
      "true",
    );

    await waitFor(() => {
      const indexOption = mocks.echartOptions.at(-1) as {
        legend?: { data?: string[]; selected?: Record<string, boolean> };
        series?: Array<{ name?: string; data?: unknown[] }>;
      };
      expect(indexOption.legend?.data).toEqual(["MA5", "MA10", "MA20", "MA60", "MA120"]);
      expect(indexOption.legend?.selected).toEqual({});
      expect(indexOption.series?.find((series) => series.name === "PE(TTM)")).toBeUndefined();
      expect(indexOption.series?.find((series) => series.name === "PB(MRQ)")).toBeUndefined();
      expect(indexOption.series?.find((series) => series.name === "K线")?.data).toHaveLength(2);
    });

    await user.click(within(screen.getByLabelText("宽基指数时间范围")).getByRole("button", { name: "近3月" }));

    expect(within(screen.getByLabelText("宽基指数时间范围")).getByRole("button", { name: "近3月" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByLabelText("沪深 300 当前时间跨度涨幅")).toHaveTextContent("区间涨幅 +1.86%");
    await waitFor(() => {
      const indexOption = mocks.echartOptions.at(-1) as {
        series?: Array<{ name?: string; data?: unknown[] }>;
      };
      expect(indexOption.series?.find((series) => series.name === "K线")?.data).toHaveLength(3);
    });
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

  it("collapses the research summary to the right so the kline canvas can expand", async () => {
    const user = userEvent.setup();
    render(<StockMarketWorkspace />);

    const overviewPanel = screen.getByRole("tabpanel", { name: "市场行情" });
    expect(overviewPanel).toHaveClass("lg:grid-cols-[minmax(0,1fr)_260px]");
    expect(screen.getByRole("complementary", { name: "研究摘要" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "折叠研究摘要" }));

    expect(overviewPanel).toHaveClass("lg:grid-cols-[minmax(0,1fr)_44px]");
    expect(screen.queryByText("最新收盘")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "展开研究摘要" })).toHaveAttribute("aria-expanded", "false");

    await user.click(screen.getByRole("button", { name: "展开研究摘要" }));

    expect(overviewPanel).toHaveClass("lg:grid-cols-[minmax(0,1fr)_260px]");
    expect(screen.getByText("最新收盘")).toBeInTheDocument();
  });

  it("shows custom date controls without duplicate refresh buttons", async () => {
    const user = userEvent.setup();
    render(<StockMarketWorkspace />);

    expect(screen.queryByRole("button", { name: "刷新基础标的" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "R1" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("起始日期")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "刷新行情数据" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "自定义" }));

    expect(screen.getByLabelText("起始日期")).toBeInTheDocument();
    expect(screen.getByLabelText("结束日期")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "R1" })).not.toBeInTheDocument();
  });

  it("refreshes the selected custom date range from the icon beside adjustment controls", async () => {
    const user = userEvent.setup();
    render(<StockMarketWorkspace />);

    await user.click(screen.getByRole("button", { name: "自定义" }));
    await user.clear(screen.getByLabelText("起始日期"));
    await user.type(screen.getByLabelText("起始日期"), "2024-01-02");
    await user.clear(screen.getByLabelText("结束日期"));
    await user.type(screen.getByLabelText("结束日期"), "2024-02-03");
    await user.click(screen.getByRole("button", { name: "刷新行情数据" }));

    expect(mocks.refresh).toHaveBeenCalledWith({
      symbol: "000001.SZ",
      range: {
        type: "custom",
        startDate: "2024-01-02",
        endDate: "2024-02-03",
      },
      financialReportType: "quarterly",
    });

    const refreshButton = screen.getByRole("button", { name: "刷新行情数据" });
    const unadjustedButton = screen.getByRole("button", { name: "不复权" });
    expect(refreshButton.compareDocumentPosition(unadjustedButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("uses the latest month as the default stock range", () => {
    render(<StockMarketWorkspace />);

    expect(mocks.detailRanges.at(-1)).toMatchObject({ type: "1m" });
    expect(screen.getByRole("button", { name: "近1月" })).toHaveAttribute("aria-pressed", "true");
  });

  it("separates overview and financial content into real tabs", async () => {
    const user = userEvent.setup();
    render(<StockMarketWorkspace />);

    expect(screen.getByRole("tab", { name: "市场行情" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "财务数据" })).toHaveAttribute("aria-selected", "false");
    expect(screen.getByRole("button", { name: "近3月" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "财务数据" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "财务数据" }));

    expect(screen.getByRole("tab", { name: "财务数据" })).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByRole("heading", { name: "财务数据" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "近3月" })).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "市场行情" }));

    expect(screen.getByRole("button", { name: "近3月" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "财务数据" })).not.toBeInTheDocument();
  });

  it("removes the redundant summary metrics and watchlist action", () => {
    render(<StockMarketWorkspace />);

    expect(screen.queryByRole("button", { name: "加入自选" })).not.toBeInTheDocument();
    expect(screen.queryByText("市盈率(TTM)")).not.toBeInTheDocument();
    expect(screen.queryByText("总市值")).not.toBeInTheDocument();
    expect(screen.queryByText(/交易中/)).not.toBeInTheDocument();
    expect(screen.queryByText(/开：/)).not.toBeInTheDocument();
    expect(screen.getByRole("img", { name: "000001.SZ 日级别行情K线" })).toHaveClass(
      "h-full",
      "min-h-[22rem]",
    );
  });

  it("shows financial metrics as secondary tabs with an independent overview-compatible range", async () => {
    const user = userEvent.setup();
    render(<StockMarketWorkspace />);

    await user.click(screen.getByRole("tab", { name: "财务数据" }));

    const revenueTab = screen.getByRole("tab", { name: "营业收入" });
    expect(revenueTab).toHaveAttribute("aria-selected", "true");
    expect(revenueTab).toHaveClass("border-accent");
    expect(screen.getByRole("tab", { name: "经营活动现金流" })).toHaveAttribute("aria-selected", "false");
    expect(screen.getByRole("img", { name: "营业收入 图表" })).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: "经营活动现金流 图表" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "近5年" })).toHaveAttribute("aria-pressed", "true");
    expect(
      within(screen.getByLabelText("财务时间范围"))
        .getAllByRole("button")
        .map((button) => button.textContent),
    ).toEqual(["近1月", "近3月", "近6月", "近1年", "近3年", "近5年", "自定义"]);
    expect(screen.getByText("+100.00%")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "经营活动现金流" }));
    expect(screen.queryByRole("img", { name: "营业收入 图表" })).not.toBeInTheDocument();
    expect(screen.getByRole("img", { name: "经营活动现金流 图表" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "近3年" }));
    expect(screen.getByRole("button", { name: "近3年" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByText("+100.00%")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "近1月" }));
    expect(screen.getByRole("button", { name: "近1月" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByText("+100.00%")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "自定义" }));
    expect(screen.getByLabelText("财务起始日期")).toHaveValue("2021-12-31");
    expect(screen.getByLabelText("财务结束日期")).toHaveValue("2025-12-31");

    await user.click(screen.getByRole("tab", { name: "市场行情" }));
    expect(screen.getByRole("button", { name: "近1月" })).toHaveAttribute("aria-pressed", "true");
  });

  it("places the report period selector in the financial range toolbar", async () => {
    const user = userEvent.setup();
    render(<StockMarketWorkspace />);

    await user.click(screen.getByRole("tab", { name: "财务数据" }));

    const toolbar = screen.getByLabelText("财务筛选工具栏");
    expect(within(toolbar).getByRole("button", { name: "季度" })).toHaveAttribute("aria-pressed", "true");
    expect(within(toolbar).getByRole("button", { name: "年度" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "财务数据" })).not.toBeInTheDocument();
  });

  it("keeps the paginator at the bottom of the viewport-height list panel", () => {
    render(<StockMarketWorkspace />);

    const panel = screen.getByTestId("instrument-list-panel");
    const detailPanel = screen.getByTestId("stock-detail-panel");
    const paginator = screen.getByLabelText("股票列表分页");

    expect(panel).toHaveClass("h-full", "min-h-0");
    expect(detailPanel).toHaveClass("h-full", "min-h-0");
    expect(within(panel).getByLabelText("股票列表分页")).toBe(paginator);
  });

  it("adapts the instrument page size to the available list height", async () => {
    render(<StockMarketWorkspace />);

    expect(mocks.instrumentFilters.at(-1)).toMatchObject({ page: 1, pageSize: 10 });
    const listBody = screen.getByTestId("instrument-list-body");
    const resizeEntry = {
      target: listBody,
      contentRect: { height: 720 },
    } as unknown as ResizeObserverEntry;

    act(() => {
      resizeObserverCallbacks[0]?.([resizeEntry], {} as ResizeObserver);
    });

    await waitFor(() => {
      expect(mocks.instrumentFilters.at(-1)).toMatchObject({ page: 1, pageSize: 15 });
    });
  });

  it("keeps the current page when a resize does not change page capacity", async () => {
    const user = userEvent.setup();
    render(<StockMarketWorkspace />);

    await user.click(screen.getByRole("button", { name: "第 2 页" }));
    const listBody = screen.getByTestId("instrument-list-body");
    const resizeEntry = {
      target: listBody,
      contentRect: { height: 500 },
    } as unknown as ResizeObserverEntry;

    act(() => {
      resizeObserverCallbacks[0]?.([resizeEntry], {} as ResizeObserver);
    });

    expect(within(screen.getByRole("table")).getByText("000011.SZ")).toBeInTheDocument();
    expect(mocks.instrumentFilters.at(-1)).toMatchObject({ page: 2, pageSize: 10 });
  });

  it("uses compact overview range controls", () => {
    render(<StockMarketWorkspace />);

    expect(screen.getByLabelText("行情时间范围")).toHaveClass("h-8");
    expect(screen.getByRole("button", { name: "近1月" })).toHaveClass("px-3", "text-xs");
    expect(screen.getByLabelText("价格复权方式")).toHaveClass("h-8");
    expect(screen.getByRole("button", { name: "不复权" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByRole("button", { name: "前复权" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "后复权" })).not.toBeInTheDocument();
  });

  it("keeps the current unadjusted price mode", () => {
    render(<StockMarketWorkspace />);

    expect(screen.getByRole("button", { name: "不复权" })).toHaveAttribute("aria-pressed", "true");
  });

  it("uses compact chart labels and places valuation legends on the right", async () => {
    render(<StockMarketWorkspace />);

    await waitFor(() => expect(mocks.echartOptions.length).toBeGreaterThan(0));
    const klineOption = mocks.echartOptions[0] as {
      legend?: {
        right?: number;
        orient?: string;
        data?: string[];
        selected?: Record<string, boolean>;
      };
      tooltip?: { padding?: number[]; textStyle?: { fontSize?: number } };
      grid?: Array<{ height?: string | number }>;
      yAxis?: Array<{ axisLabel?: { show?: boolean; fontSize?: number } }>;
      series?: Array<{ name?: string; data?: Array<number | null> }>;
    };
    const seriesByName = Object.fromEntries(
      (klineOption.series ?? []).map((series) => [series.name, series]),
    );

    expect(klineOption.legend?.right).toBe(8);
    expect(klineOption.legend?.orient).toBe("vertical");
    expect(klineOption.legend?.data).toEqual(
      expect.arrayContaining(["PE(TTM)", "PB(MRQ)", "股息率(TTM)", "总市值"]),
    );
    expect(klineOption.legend?.selected).toEqual({
      "PE(TTM)": false,
      "PB(MRQ)": false,
      "股息率(TTM)": false,
      总市值: false,
    });
    expect(seriesByName["PE(TTM)"]?.data).toEqual([5.1, null]);
    expect(klineOption.tooltip?.textStyle?.fontSize).toBe(10);
    expect(klineOption.tooltip?.padding).toEqual([6, 8]);
    expect(klineOption.grid?.[0]?.height).toBe("56%");
    expect(klineOption.yAxis?.[0]?.axisLabel?.fontSize).toBe(10);
    expect(klineOption.yAxis?.[1]?.axisLabel?.show).toBe(false);
  });

  it("uses smaller financial controls and keeps the chart in a flexible panel", async () => {
    const user = userEvent.setup();
    render(<StockMarketWorkspace />);

    await user.click(screen.getByRole("tab", { name: "财务数据" }));

    expect(screen.getByRole("tab", { name: "营业收入" })).toHaveClass("text-xs");
    expect(screen.getByRole("tab", { name: "ROE" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "营收同比" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "净利润同比" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "资产负债率" })).toBeInTheDocument();
    expect(screen.getByLabelText("财务时间范围")).toHaveClass("h-8");
    expect(screen.getByLabelText("财报周期")).toHaveClass("h-8", "text-xs");
    expect(screen.getByRole("img", { name: "营业收入 图表" })).toHaveClass("min-h-0", "flex-1");

    await user.click(screen.getByRole("tab", { name: "ROE" }));
    await waitFor(() => {
      const roeOption = mocks.echartOptions.find((option) =>
        JSON.stringify(option).includes('"name":"ROE"'),
      ) as { series?: Array<{ type?: string }> } | undefined;
      expect(roeOption?.series?.[0]?.type).toBe("line");
    });
  });

  it("shows complete instrument information when hovering a list row", () => {
    render(<StockMarketWorkspace />);

    expect(screen.getByText("名称较长的测试股票股份有限公司").closest("tr")).toHaveAttribute(
      "title",
      "代码：000002.SZ；名称：名称较长的测试股票股份有限公司；市场：深市；类型：股票；最新价：11.000",
    );
  });
});
