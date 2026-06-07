import * as echarts from "echarts";
import {
  ArrowPathIcon,
  CalendarDaysIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  MagnifyingGlassIcon,
} from "@heroicons/react/24/outline";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useStockMarketDetailQuery } from "../hooks/use-stock-market-detail-query";
import { useStockMarketInstrumentsQuery } from "../hooks/use-stock-market-instruments-query";
import { useStockMarketRefreshMutation } from "../hooks/use-stock-market-refresh-mutation";
import type {
  MarketDataRangeSelection,
  StockDailyBar,
  StockFinancialReportType,
  StockFinancialSeries,
  StockInstrument,
} from "../model/market-data.types";
import { formatLocalDateTime } from "../../../shared/utils/format-local-date-time";

const STOCK_RANGE_OPTIONS = [
  { value: "1m", label: "近1月", months: 1 },
  { value: "3m", label: "近3月", months: 3 },
  { value: "6m", label: "近6月", months: 6 },
  { value: "1y", label: "近1年", months: 12 },
  { value: "3y", label: "近3年", months: 36 },
  { value: "5y", label: "近5年", months: 60 },
  { value: "custom", label: "自定义", months: null },
] as const;

const MARKET_BOARD_OPTIONS = [
  { value: "all", label: "全部" },
  { value: "沪市主板", label: "沪市主板" },
  { value: "深市主板", label: "深市主板" },
  { value: "科创板", label: "科创板" },
  { value: "创业板", label: "创业板" },
  { value: "北交所", label: "北交所" },
  { value: "ETF", label: "ETF" },
];

const INSTRUMENT_TYPE_OPTIONS = [
  { value: "all", label: "全部" },
  { value: "stock", label: "股票" },
  { value: "etf", label: "ETF" },
];

const LISTING_STATUS_OPTIONS = [
  { value: "all", label: "全部" },
  { value: "listed", label: "上市" },
];

const FINANCIAL_ORDER = ["revenue", "expense", "cash_flow", "asset", "liability"];
const DEFAULT_INSTRUMENT_PAGE_SIZE = 10;
const INSTRUMENT_TABLE_HEADER_HEIGHT = 41;
const INSTRUMENT_ROW_HEIGHT = 43;
type StockDetailTab = "overview" | "financial";
type StockPriceAdjustment = "none" | "forward" | "backward";

/**
 * 渲染股票市场页，布局对齐截图中的交易终端式信息密度。
 */
export function StockMarketWorkspace() {
  const [searchText, setSearchText] = useState("");
  const [instrumentType, setInstrumentType] = useState("all");
  const [marketBoard, setMarketBoard] = useState("all");
  const [listingStatus, setListingStatus] = useState("all");
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [range, setRange] = useState<MarketDataRangeSelection>({ type: "1m" });
  const [financialReportType, setFinancialReportType] = useState<StockFinancialReportType>("quarterly");
  const [financialRange, setFinancialRange] = useState<MarketDataRangeSelection>({ type: "5y" });
  const [activeFinancialMetric, setActiveFinancialMetric] = useState(FINANCIAL_ORDER[0]);
  const [instrumentPage, setInstrumentPage] = useState(1);
  const [instrumentPageSize, setInstrumentPageSize] = useState(DEFAULT_INSTRUMENT_PAGE_SIZE);
  const instrumentPageSizeRef = useRef(DEFAULT_INSTRUMENT_PAGE_SIZE);
  const [isInstrumentListCollapsed, setIsInstrumentListCollapsed] = useState(false);
  const [activeDetailTab, setActiveDetailTab] = useState<StockDetailTab>("overview");
  const [priceAdjustment, setPriceAdjustment] = useState<StockPriceAdjustment>("none");

  const instrumentsQuery = useStockMarketInstrumentsQuery({
    query: searchText,
    instrumentType,
    marketBoard,
    listingStatus,
    page: instrumentPage,
    pageSize: instrumentPageSize,
  });
  const detailQuery = useStockMarketDetailQuery(selectedSymbol, range, financialReportType);
  const refreshMutation = useStockMarketRefreshMutation(selectedSymbol, range, financialReportType);
  const instruments = instrumentsQuery.data?.items ?? [];
  const instrumentTotal = instrumentsQuery.data?.total ?? 0;
  const instrumentPageCount = Math.max(1, Math.ceil(instrumentTotal / instrumentPageSize));

  useEffect(() => {
    if (instrumentsQuery.isPending) return;
    if (instruments.length === 0) {
      setSelectedSymbol(null);
      return;
    }
    if (!selectedSymbol || !instruments.some((instrument) => instrument.symbol === selectedSymbol)) {
      setSelectedSymbol(instruments[0].symbol);
    }
  }, [instruments, instrumentsQuery.isPending, selectedSymbol]);

  useEffect(() => {
    if (instrumentsQuery.isPending || instrumentPage <= instrumentPageCount) return;
    setInstrumentPage(instrumentPageCount);
  }, [instrumentPage, instrumentPageCount, instrumentsQuery.isPending]);

  /** 更新搜索词并回到筛选结果第一页。 */
  function handleSearchTextChange(value: string) {
    setSearchText(value);
    setInstrumentPage(1);
  }

  /** 更新证券类型并回到筛选结果第一页。 */
  function handleInstrumentTypeChange(value: string) {
    setInstrumentType(value);
    setInstrumentPage(1);
  }

  /** 更新市场板块并回到筛选结果第一页。 */
  function handleMarketBoardChange(value: string) {
    setMarketBoard(value);
    setInstrumentPage(1);
  }

  /** 更新上市状态并回到筛选结果第一页。 */
  function handleListingStatusChange(value: string) {
    setListingStatus(value);
    setInstrumentPage(1);
  }

  /** 根据列表容器高度更新每页条数，并回到第一页避免分页偏移。 */
  const handleInstrumentPageSizeChange = useCallback((pageSize: number) => {
    if (instrumentPageSizeRef.current === pageSize) return;
    instrumentPageSizeRef.current = pageSize;
    setInstrumentPageSize(pageSize);
    setInstrumentPage(1);
  }, []);

  const selectedInstrument = useMemo(
    () => instruments.find((item) => item.symbol === selectedSymbol) ?? detailQuery.data?.instrument ?? null,
    [detailQuery.data?.instrument, instruments, selectedSymbol],
  );
  const latestBar = detailQuery.data?.daily_bars.at(-1) ?? null;
  const previousBar = detailQuery.data?.daily_bars.at(-2) ?? null;
  const priceChange = latestBar && previousBar ? latestBar.close - previousBar.close : 0;
  const priceChangeRate = latestBar && previousBar && previousBar.close !== 0 ? (priceChange / previousBar.close) * 100 : 0;

  return (
    <div className="-m-8 flex h-[calc(100vh-4.75rem)] min-h-[40rem] flex-col overflow-hidden bg-[#f5f7fb] text-slate-700">
      <HeaderBand />
      <FilterBand
        instrumentType={instrumentType}
        listingStatus={listingStatus}
        marketBoard={marketBoard}
        onInstrumentTypeChange={handleInstrumentTypeChange}
        onListingStatusChange={handleListingStatusChange}
        onMarketBoardChange={handleMarketBoardChange}
        onSearchTextChange={handleSearchTextChange}
        searchText={searchText}
      />

      <div
        className={`grid min-h-0 flex-1 grid-cols-1 items-stretch gap-2 overflow-hidden border-t border-slate-200 px-0 py-2 ${
          isInstrumentListCollapsed
            ? "xl:grid-cols-[48px_minmax(0,1fr)]"
            : "xl:grid-cols-[384px_minmax(0,1fr)]"
        }`}
      >
        <InstrumentListPanel
          currentPage={instrumentPage}
          instruments={instruments}
          isCollapsed={isInstrumentListCollapsed}
          isError={instrumentsQuery.isError}
          isPending={instrumentsQuery.isPending}
          onCollapseChange={setIsInstrumentListCollapsed}
          onPageChange={setInstrumentPage}
          onPageSizeChange={handleInstrumentPageSizeChange}
          onSelect={setSelectedSymbol}
          pageSize={instrumentPageSize}
          selectedSymbol={selectedSymbol}
          total={instrumentTotal}
          warning={instrumentsQuery.data?.warning_message ?? ""}
        />

        <section
          className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden bg-white"
          data-testid="stock-detail-panel"
        >
          {selectedInstrument ? (
            <>
              <StockSummaryHeader
                instrument={selectedInstrument}
              />
              <StockDetailTabs activeTab={activeDetailTab} onTabChange={setActiveDetailTab} />
              {activeDetailTab === "overview" ? (
                <div
                  aria-labelledby="stock-detail-tab-overview"
                  className="flex min-h-0 flex-1 p-3"
                  id="stock-detail-panel-overview"
                  role="tabpanel"
                >
                  <main className="flex min-h-0 min-w-0 flex-1 flex-col">
                    <RangeToolbar
                      endDate={range.endDate}
                      onRangeChange={setRange}
                      onPriceAdjustmentChange={setPriceAdjustment}
                      onRefresh={() => refreshMutation.mutate()}
                      priceAdjustment={priceAdjustment}
                      range={range}
                      refreshPending={refreshMutation.isPending}
                      startDate={range.startDate}
                    />
                    <KlinePanel
                      bars={detailQuery.data?.daily_bars ?? []}
                      isError={detailQuery.isError}
                      isPending={detailQuery.isPending}
                      symbol={selectedInstrument.symbol}
                      warning={detailQuery.data?.sync_state.warning_message ?? ""}
                    />
                  </main>

                  {/*<aside className="space-y-3">*/}
                  {/*  <SideInfoPanel*/}
                  {/*    title="基础信息"*/}
                  {/*    rows={[*/}
                  {/*      ["股票代码", selectedInstrument.symbol],*/}
                  {/*      ["所属交易所", selectedInstrument.exchange === "SH" ? "上海证券交易所" : selectedInstrument.exchange === "SZ" ? "深圳证券交易所" : "北京证券交易所"],*/}
                  {/*      ["上市日期", detailQuery.data?.profile.listing_date || "--"],*/}
                  {/*      ["所属板块", detailQuery.data?.profile.sector || selectedInstrument.market_board],*/}
                  {/*      ["行业", detailQuery.data?.profile.industry || "--"],*/}
                  {/*      ["地区", detailQuery.data?.profile.region || "--"],*/}
                  {/*    ]}*/}
                  {/*  />*/}
                  {/*  <SideInfoPanel*/}
                  {/*    title="行情数据"*/}
                  {/*    rows={[*/}
                  {/*      ["最新价", latestBar ? formatNumber(latestBar.close, 2) : "--"],*/}
                  {/*      ["涨跌额", latestBar ? formatSigned(priceChange, 2) : "--"],*/}
                  {/*      ["涨跌幅", latestBar ? `${formatSigned(priceChangeRate, 2)}%` : "--"],*/}
                  {/*      ["成交量", latestBar ? formatCompactNumber(latestBar.volume) : "--"],*/}
                  {/*      ["最高价", latestBar ? formatNumber(latestBar.high, 2) : "--"],*/}
                  {/*      ["最低价", latestBar ? formatNumber(latestBar.low, 2) : "--"],*/}
                  {/*      ["同步时间", detailQuery.data?.sync_state.synced_at ? formatLocalDateTime(detailQuery.data.sync_state.synced_at) : "--"],*/}
                  {/*    ]}*/}
                  {/*    valueTone*/}
                  {/*  />*/}
                  {/*</aside>*/}
                </div>
              ) : (
                <div
                  aria-labelledby="stock-detail-tab-financial"
                  className="min-h-0 flex-1 overflow-hidden p-3"
                  id="stock-detail-panel-financial"
                  role="tabpanel"
                >
                  <FinancialCards
                    activeMetric={activeFinancialMetric}
                    financialRange={financialRange}
                    isPending={detailQuery.isPending}
                    onFinancialRangeChange={setFinancialRange}
                    onMetricChange={setActiveFinancialMetric}
                    onReportTypeChange={setFinancialReportType}
                    reportType={financialReportType}
                    series={detailQuery.data?.financials.series ?? []}
                  />
                </div>
              )}
            </>
          ) : (
            <EmptySurface text={instrumentsQuery.data?.warning_message || "请刷新基础标的或选择一只股票。"} />
          )}
        </section>
      </div>
    </div>
  );
}

function HeaderBand() {
  return (
    <div className="flex h-14 items-center border-b border-slate-200 bg-white px-6">
      <div className="text-base font-semibold text-slate-500">
        Market Data
        <span className="px-3 text-slate-300">/</span>
        <span className="text-slate-950">股票市场</span>
      </div>
    </div>
  );
}

function FilterBand(props: {
  searchText: string;
  instrumentType: string;
  marketBoard: string;
  listingStatus: string;
  onSearchTextChange: (value: string) => void;
  onInstrumentTypeChange: (value: string) => void;
  onMarketBoardChange: (value: string) => void;
  onListingStatusChange: (value: string) => void;
}) {
  return (
    <div className="flex min-h-20 flex-wrap items-center gap-6 border-b border-slate-200 bg-white px-6 py-4">
      <div className="flex h-10 w-full max-w-[320px] items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-sm shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
        <input
          className="min-w-0 flex-1 bg-transparent text-slate-700 outline-none placeholder:text-slate-400"
          onChange={(event) => props.onSearchTextChange(event.target.value)}
          placeholder="搜索股票代码 / 名称"
          type="search"
          value={props.searchText}
        />
        <MagnifyingGlassIcon aria-hidden="true" className="h-5 w-5 text-slate-400" />
      </div>
      <TopSelect label="证券类型" onChange={props.onInstrumentTypeChange} options={INSTRUMENT_TYPE_OPTIONS} value={props.instrumentType} />
      <TopSelect label="市场类型" onChange={props.onMarketBoardChange} options={MARKET_BOARD_OPTIONS} value={props.marketBoard} />
      <TopSelect label="上市状态" onChange={props.onListingStatusChange} options={LISTING_STATUS_OPTIONS} value={props.listingStatus} />
    </div>
  );
}

function TopSelect(props: {
  label: string;
  options: Array<{ value: string; label: string }>;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="flex items-center gap-3 text-sm font-semibold text-slate-700">
      {props.label}
      <select
        className="h-10 min-w-36 rounded-md border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 outline-none shadow-[0_1px_2px_rgba(15,23,42,0.04)] focus:border-blue-400"
        onChange={(event) => props.onChange(event.target.value)}
        value={props.value}
      >
        {props.options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function InstrumentListPanel(props: {
  instruments: StockInstrument[];
  total: number;
  currentPage: number;
  pageSize: number;
  selectedSymbol: string | null;
  isCollapsed: boolean;
  isPending: boolean;
  isError: boolean;
  warning: string;
  onSelect: (symbol: string) => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  onCollapseChange: (collapsed: boolean) => void;
}) {
  const listBodyRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const listBody = listBodyRef.current;
    if (props.isCollapsed || !listBody || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(([entry]) => {
      const nextPageSize = calculateInstrumentPageSize(entry?.contentRect.height ?? 0);
      props.onPageSizeChange(nextPageSize);
    });
    observer.observe(listBody);
    return () => observer.disconnect();
  }, [props.isCollapsed, props.onPageSizeChange]);

  if (props.isCollapsed) {
    return (
      <aside
        className="flex h-full min-h-0 items-start justify-center bg-white pt-5"
        data-testid="instrument-list-panel"
      >
        <button
          aria-expanded="false"
          aria-label="展开股票列表"
          className="inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          onClick={() => props.onCollapseChange(false)}
          type="button"
        >
          <ChevronRightIcon aria-hidden="true" className="h-4 w-4" />
        </button>
      </aside>
    );
  }

  const totalPages = Math.max(1, Math.ceil(props.total / props.pageSize));
  const paginationItems = buildPaginationItems(props.currentPage, totalPages);

  return (
    <aside
      className="flex h-full min-h-0 flex-col overflow-hidden bg-white"
      data-testid="instrument-list-panel"
    >
      <div className="flex h-14 items-center justify-between border-b border-slate-200 px-5">
        <div className="text-sm font-semibold text-slate-950">
          全部标的
          <span className="ml-4 text-slate-500">{formatNumber(props.total)} 只</span>
        </div>
        <button
          aria-expanded="true"
          aria-label="折叠股票列表"
          className="inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          onClick={() => props.onCollapseChange(true)}
          type="button"
        >
          <ChevronLeftIcon aria-hidden="true" className="h-4 w-4" />
        </button>
      </div>
      <div
        className="min-h-0 flex-1 overflow-hidden"
        data-testid="instrument-list-body"
        ref={listBodyRef}
      >
        {props.isPending ? (
          <EmptySurface text="股票列表加载中..." />
        ) : props.isError ? (
          <EmptySurface danger text="股票列表加载失败。" />
        ) : props.instruments.length === 0 ? (
          <EmptySurface text={props.warning || "暂无匹配标的。"} />
        ) : (
          <table className="w-full table-fixed border-collapse text-left text-xs">
            <thead className="bg-white text-slate-500">
              <tr className="border-b border-slate-200">
                <th className="w-[96px] px-4 py-3 font-semibold">代码</th>
                <th className="px-3 py-3 font-semibold">名称</th>
                <th className="w-[80px] px-3 py-3 font-semibold">市场</th>
                <th className="w-[58px] px-3 py-3 font-semibold">类型</th>
                <th className="w-[72px] px-4 py-3 text-right font-semibold">最新价</th>
              </tr>
            </thead>
            <tbody>
              {props.instruments.map((instrument) => (
                <InstrumentRow
                  instrument={instrument}
                  key={instrument.symbol}
                  onSelect={props.onSelect}
                  selected={instrument.symbol === props.selectedSymbol}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>
      <nav
        aria-label="股票列表分页"
        className="flex h-14 shrink-0 items-center gap-3 border-t border-slate-200 px-4 text-xs text-slate-500"
      >
        <button
          aria-label="上一页"
          className="inline-flex h-7 w-7 items-center justify-center rounded border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-300"
          disabled={props.currentPage <= 1}
          onClick={() => props.onPageChange(props.currentPage - 1)}
          type="button"
        >
          <ChevronLeftIcon aria-hidden="true" className="h-3.5 w-3.5" />
        </button>
        {paginationItems.map((item) =>
          typeof item === "number" ? (
            <button
              aria-current={item === props.currentPage ? "page" : undefined}
              aria-label={`第 ${item} 页`}
              className={`inline-flex h-7 min-w-7 items-center justify-center rounded px-1 font-semibold ${
                item === props.currentPage
                  ? "bg-blue-600 text-white"
                  : "text-slate-500 hover:bg-slate-50"
              }`}
              key={item}
              onClick={() => props.onPageChange(item)}
              type="button"
            >
              {item}
            </button>
          ) : (
            <span aria-hidden="true" key={item}>...</span>
          ),
        )}
        <button
          aria-label="下一页"
          className="inline-flex h-7 w-7 items-center justify-center rounded border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-300"
          disabled={props.currentPage >= totalPages}
          onClick={() => props.onPageChange(props.currentPage + 1)}
          type="button"
        >
          <ChevronRightIcon aria-hidden="true" className="h-3.5 w-3.5" />
        </button>
        <span className="ml-auto"> {formatNumber(props.total)} </span>
      </nav>
    </aside>
  );
}

/**
 * 渲染单个标的行，并在鼠标悬停时展示完整列表信息。
 * @param props 标的数据、选中状态与点击回调。
 * @returns 可选择的标的表格行。
 */
function InstrumentRow(props: {
  instrument: StockInstrument;
  selected: boolean;
  onSelect: (symbol: string) => void;
}) {
  const latestPrice = props.instrument.latest_price;
  const priceTone = latestPrice === undefined || latestPrice === null ? "text-slate-400" : "text-rose-500";
  const marketLabel = props.instrument.market_board.replace("主板", "");
  const typeLabel = props.instrument.instrument_type === "etf" ? "ETF" : "股票";
  const latestPriceLabel = latestPrice === undefined || latestPrice === null ? "--" : formatNumber(latestPrice, 3);
  const hoverDescription = `代码：${props.instrument.symbol}；名称：${props.instrument.name}；市场：${marketLabel}；类型：${typeLabel}；最新价：${latestPriceLabel}`;
  return (
    <tr
      className={`cursor-pointer border-b border-slate-100 text-slate-700 hover:bg-blue-50 ${
        props.selected ? "bg-blue-50" : ""
      }`}
      onClick={() => props.onSelect(props.instrument.symbol)}
      title={hoverDescription}
    >
      <td className="px-4 py-2.5 font-semibold">{props.instrument.symbol}</td>
      <td className="truncate px-3 py-2.5 font-semibold text-slate-800">{props.instrument.name}</td>
      <td className="px-3 py-2.5 text-slate-600">{marketLabel}</td>
      <td className="px-3 py-2.5 text-slate-600">{typeLabel}</td>
      <td className={`px-4 py-2.5 text-right font-semibold ${priceTone}`}>
        {latestPriceLabel}
      </td>
    </tr>
  );
}

function StockSummaryHeader(props: { instrument: StockInstrument }) {
  return (
    <header className="px-6 pb-3 pt-4">
      <div className="min-w-[320px]">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-2xl font-bold text-slate-950">
            {props.instrument.symbol}
            <span className="ml-4">{props.instrument.name}</span>
          </h2>
          <span className="rounded-md bg-blue-50 px-3 py-1 text-sm font-semibold text-slate-600">{props.instrument.market_board}</span>
        </div>
        <div className="mt-1 text-xs font-medium text-slate-400">{props.instrument.name}股份有限公司</div>
      </div>
    </header>
  );
}

/**
 * 渲染股票详情一级页签，仅保留行情概览与财务数据两个真实内容区。
 */
function StockDetailTabs(props: {
  activeTab: StockDetailTab;
  onTabChange: (tab: StockDetailTab) => void;
}) {
  const tabs: Array<{ value: StockDetailTab; label: string }> = [
    { value: "overview", label: "市场行情" },
    { value: "financial", label: "财务数据" },
  ];

  return (
    <div aria-label="股票详情" className="flex h-12 items-end gap-8 border-b border-slate-200 px-6" role="tablist">
      {tabs.map((tab) => {
        const isActive = props.activeTab === tab.value;
        return (
          <button
            aria-controls={`stock-detail-panel-${tab.value}`}
            aria-selected={isActive}
            className={`relative h-12 px-1 text-sm font-semibold ${
              isActive ? "text-blue-600" : "text-slate-500 hover:text-slate-800"
            }`}
            id={`stock-detail-tab-${tab.value}`}
            key={tab.value}
            onClick={() => props.onTabChange(tab.value)}
            role="tab"
            type="button"
          >
            {tab.label}
            {isActive ? <span className="absolute inset-x-0 bottom-0 h-0.5 rounded-full bg-blue-600" /> : null}
          </button>
        );
      })}
    </div>
  );
}

function RangeToolbar(props: {
  range: MarketDataRangeSelection;
  priceAdjustment: StockPriceAdjustment;
  startDate?: string;
  endDate?: string;
  refreshPending: boolean;
  onRangeChange: (range: MarketDataRangeSelection) => void;
  onPriceAdjustmentChange: (adjustment: StockPriceAdjustment) => void;
  onRefresh: () => void;
}) {
  const [startDate, setStartDate] = useState(props.startDate ?? "2025-03-05");
  const [endDate, setEndDate] = useState(props.endDate ?? "2025-06-05");
  return (
    <div className="flex shrink-0 flex-wrap items-center gap-2">
      <div
        aria-label="行情时间范围"
        className="inline-flex h-8 overflow-hidden rounded-md border border-slate-200 bg-white"
      >
        {STOCK_RANGE_OPTIONS.map((option) => (
          <button
            className={`border-r border-slate-100 px-3 text-xs font-semibold last:border-r-0 ${
              props.range.type === option.value ? "bg-blue-50 text-slate-950" : "text-slate-500 hover:bg-slate-50"
            }`}
            key={option.value}
            onClick={() =>
              props.onRangeChange(
                option.value === "custom"
                  ? { type: "custom", startDate, endDate }
                  : { type: option.value },
              )
            }
            type="button"
          >
            {option.label}
          </button>
        ))}
      </div>
      {props.range.type === "custom" ? (
        <label className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-500">
          <input
            aria-label="起始日期"
            className="w-28 bg-transparent text-slate-700 outline-none"
            onChange={(event) => {
              setStartDate(event.target.value);
              props.onRangeChange({ type: "custom", startDate: event.target.value, endDate });
            }}
            type="date"
            value={startDate}
          />
          <span>至</span>
          <input
            aria-label="结束日期"
            className="w-28 bg-transparent text-slate-700 outline-none"
            onChange={(event) => {
              setEndDate(event.target.value);
              props.onRangeChange({ type: "custom", startDate, endDate: event.target.value });
            }}
            type="date"
            value={endDate}
          />
          <CalendarDaysIcon aria-hidden="true" className="h-4 w-4 text-slate-400" />
        </label>
      ) : null}
      <div className="ml-auto flex items-center gap-2">
        <button
          aria-label="刷新行情数据"
          className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-blue-600 shadow-sm hover:bg-blue-50 disabled:cursor-not-allowed disabled:text-slate-300"
          disabled={props.refreshPending}
          onClick={props.onRefresh}
          title="刷新选中时间范围内的行情数据"
          type="button"
        >
          <ArrowPathIcon
            aria-hidden="true"
            className={`h-4 w-4 ${props.refreshPending ? "animate-spin" : ""}`}
          />
        </button>
        <div
          aria-label="价格复权方式"
          className="inline-flex h-8 overflow-hidden rounded-full border border-slate-200 bg-white text-xs font-semibold"
        >
          {(
            [
              { value: "none", label: "不复权" },
              // { value: "forward", label: "前复权" },
              // { value: "backward", label: "后复权" },
            ] as const
          ).map((option) => {
            const isSelected = props.priceAdjustment === option.value;
            return (
              <button
                aria-pressed={isSelected}
                className={`border-r border-slate-200 px-3 last:border-r-0 ${
                  isSelected
                    ? "bg-slate-900 text-white"
                    : "text-slate-500 hover:bg-slate-50 hover:text-slate-800"
                }`}
                key={option.value}
                onClick={() => props.onPriceAdjustmentChange(option.value)}
                type="button"
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function KlinePanel(props: {
  bars: StockDailyBar[];
  symbol: string;
  isPending: boolean;
  isError: boolean;
  warning: string;
}) {
  if (props.isPending) return <EmptySurface text="行情数据加载中..." />;
  if (props.isError) return <EmptySurface danger text="行情数据加载失败。" />;
  if (props.bars.length === 0) return <EmptySurface text={props.warning || "当前时间范围暂无行情数据。"} />;
  return (
    <section className="flex min-h-0 flex-1 border-b border-slate-200 bg-white pb-2">
      <KlineChart bars={props.bars} symbol={props.symbol} />
    </section>
  );
}

function KlineChart(props: { bars: StockDailyBar[]; symbol: string }) {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const option = useMemo((): echarts.EChartsOption => {
    const labels = props.bars.map((bar) => bar.date);
    return {
      animation: false,
      tooltip: {
        trigger: "axis",
        confine: true,
        padding: [6, 8],
        textStyle: { fontSize: 10, lineHeight: 15 },
        axisPointer: { type: "cross" },
      },
      legend: {
        top: 5,
        left: "center",
        type: "scroll",
        itemWidth: 16,
        itemHeight: 8,
        textStyle: { color: "#64748b", fontSize: 11 },
        data: ["K线", "MA5", "MA10", "MA20", "MA60", "MA120"],
      },
      grid: [
        { left: 54, right: 22, top: 38, height: "56%" },
        { left: 54, right: 22, top: "70%", height: "14%" },
      ],
      xAxis: [
        {
          type: "category",
          data: labels,
          boundaryGap: true,
          axisLabel: { color: "#64748b", fontSize: 10 },
          axisLine: { lineStyle: { color: "#dbe3ee" } },
        },
        {
          type: "category",
          data: labels,
          gridIndex: 1,
          boundaryGap: true,
          axisLabel: { color: "#94a3b8", fontSize: 10 },
        },
      ],
      yAxis: [
        {
          type: "value",
          scale: true,
          axisLabel: { color: "#64748b", fontSize: 10 },
          splitLine: { lineStyle: { color: "#edf2f7" } },
        },
        {
          type: "value",
          gridIndex: 1,
          axisLabel: { show: false },
          axisTick: { show: false },
          axisLine: { show: false },
          splitLine: { lineStyle: { color: "#edf2f7" } },
        },
      ],
      dataZoom: [
        { type: "inside", xAxisIndex: [0, 1] },
        { type: "slider", xAxisIndex: [0, 1], bottom: 0, height: 24, borderColor: "#dbeafe", fillerColor: "rgba(59,130,246,0.16)" },
      ],
      series: [
        {
          name: "K线",
          type: "candlestick",
          data: props.bars.map((bar) => [bar.open, bar.close, bar.low, bar.high]),
          itemStyle: { color: "#ef4444", color0: "#10b981", borderColor: "#ef4444", borderColor0: "#10b981" },
        },
        lineSeries("MA5", props.bars.map((bar) => bar.ma5), "#f59e0b"),
        lineSeries("MA10", props.bars.map((bar) => bar.ma10), "#38bdf8"),
        lineSeries("MA20", props.bars.map((bar) => bar.ma20), "#a78bfa"),
        lineSeries("MA60", props.bars.map((bar) => bar.ma60), "#34d399"),
        lineSeries("MA120", props.bars.map((bar) => bar.ma120), "#93c5fd"),
        {
          name: "成交量",
          type: "bar",
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: props.bars.map((bar) => bar.volume),
          itemStyle: {
            color: (params: { dataIndex: number }) => {
              const bar = props.bars[params.dataIndex];
              return bar.close >= bar.open ? "#ef4444" : "#10b981";
            },
          },
        },
      ],
    };
  }, [props.bars]);

  useEffect(() => {
    if (!chartRef.current) return;
    const instance = echarts.init(chartRef.current, undefined, { renderer: "svg" });
    instance.setOption(option);
    const isTestRuntime =
      typeof navigator !== "undefined" && navigator.userAgent.toLowerCase().includes("jsdom");
    const observer =
      !isTestRuntime && typeof ResizeObserver !== "undefined"
        ? new ResizeObserver(() => instance.resize())
        : null;
    observer?.observe(chartRef.current);
    return () => {
      observer?.disconnect();
      instance.dispose();
    };
  }, [option]);

  return (
    <div
      ref={chartRef}
      aria-label={`${props.symbol} 日级别行情K线`}
      className="h-full min-h-[22rem] w-full"
      role="img"
    />
  );
}

function FinancialCards(props: {
  activeMetric: string;
  financialRange: MarketDataRangeSelection;
  isPending: boolean;
  reportType: StockFinancialReportType;
  series: StockFinancialSeries[];
  onFinancialRangeChange: (range: MarketDataRangeSelection) => void;
  onMetricChange: (metric: string) => void;
  onReportTypeChange: (type: StockFinancialReportType) => void;
}) {
  const sortedSeries = FINANCIAL_ORDER.map((metric) => props.series.find((item) => item.metric === metric)).filter(
    (item): item is StockFinancialSeries => Boolean(item),
  );
  const selectedSeries = sortedSeries.find((item) => item.metric === props.activeMetric) ?? sortedSeries[0];
  const visibleSeries = selectedSeries
    ? filterFinancialSeriesByRange(selectedSeries, props.financialRange)
    : null;

  return (
    <section className="flex h-full min-h-0 flex-col gap-3">
      {!props.isPending && sortedSeries.some((item) => item.points.length > 0) ? (
        <div
          aria-label="财务指标"
          className="flex h-10 shrink-0 items-end gap-7 border-b border-slate-200"
          role="tablist"
        >
          {sortedSeries.map((item) => {
            const isActive = item.metric === selectedSeries?.metric;
            return (
              <button
                aria-controls={`financial-metric-panel-${item.metric}`}
                aria-selected={isActive}
                className={`relative h-10 border-b-2 px-1 text-xs font-semibold ${
                  isActive
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-slate-500 hover:text-slate-800"
                }`}
                id={`financial-metric-tab-${item.metric}`}
                key={item.metric}
                onClick={() => props.onMetricChange(item.metric)}
                role="tab"
                type="button"
              >
                {item.label}
              </button>
            );
          })}
        </div>
      ) : null}
      <div
        aria-label="财务筛选工具栏"
        className="flex shrink-0 flex-wrap items-center gap-2 border-b border-slate-200 pb-3"
      >
        {/*<span className="text-xs font-semibold text-slate-500">时间范围</span>*/}
        <div aria-label="财务时间范围" className="inline-flex h-8 overflow-hidden rounded-md border border-slate-200 bg-white">
          {STOCK_RANGE_OPTIONS.map((option) => (
            <button
              className={`border-r border-slate-100 px-3 text-xs font-semibold last:border-r-0 ${
                props.financialRange.type === option.value
                  ? "bg-blue-50 text-slate-950"
                  : "text-slate-500 hover:bg-slate-50"
              }`}
              key={option.value}
              onClick={() =>
                props.onFinancialRangeChange(
                  option.value === "custom"
                    ? {
                        type: "custom",
                        startDate: props.financialRange.startDate ?? selectedSeries?.points[0]?.period ?? "",
                        endDate: props.financialRange.endDate ?? selectedSeries?.points.at(-1)?.period ?? "",
                      }
                    : { type: option.value },
                )
              }
              type="button"
            >
              {option.label}
            </button>
          ))}
        </div>
        {props.financialRange.type === "custom" ? (
          <label className="inline-flex h-8 items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-500">
            <input
              aria-label="财务起始日期"
              className="w-28 bg-transparent text-slate-700 outline-none"
              onChange={(event) =>
                props.onFinancialRangeChange({
                  ...props.financialRange,
                  startDate: event.target.value,
                })
              }
              type="date"
              value={props.financialRange.startDate ?? ""}
            />
            <span>至</span>
            <input
              aria-label="财务结束日期"
              className="w-28 bg-transparent text-slate-700 outline-none"
              onChange={(event) =>
                props.onFinancialRangeChange({
                  ...props.financialRange,
                  endDate: event.target.value,
                })
              }
              type="date"
              value={props.financialRange.endDate ?? ""}
            />
            <CalendarDaysIcon aria-hidden="true" className="h-4 w-4 text-slate-400" />
          </label>
        ) : null}
        <div
          aria-label="财报周期"
          className="ml-auto inline-flex h-8 overflow-hidden rounded-full border border-slate-200 bg-white text-xs font-semibold"
        >
          {(["quarterly", "yearly"] as const).map((type) => (
            <button
              className={`px-4 ${
                props.reportType === type
                  ? "bg-slate-900 text-white"
                  : "text-slate-500 hover:bg-slate-50 hover:text-slate-800"
              }`}
              key={type}
              onClick={() => props.onReportTypeChange(type)}
              type="button"
            >
              {type === "quarterly" ? "季度" : "年度"}
            </button>
          ))}
        </div>
      </div>
      {props.isPending ? (
        <EmptySurface text="财报数据加载中..." />
      ) : sortedSeries.every((item) => item.points.length === 0) ? (
        <EmptySurface text="当前标的暂无可展示财报数据。" />
      ) : (
        <>
          {visibleSeries && visibleSeries.points.length > 0 ? (
            <div
              aria-labelledby={`financial-metric-tab-${visibleSeries.metric}`}
              className="min-h-0 flex-1"
              id={`financial-metric-panel-${visibleSeries.metric}`}
              role="tabpanel"
            >
              <FinancialMetricCard series={visibleSeries} />
            </div>
          ) : (
            <EmptySurface text="当前时间范围暂无可展示财报数据。" />
          )}
        </>
      )}
    </section>
  );
}

/**
 * 按所选时间范围裁剪单项财务序列，预设范围使用该序列最新报告期作为终点。
 * @param series 原始财务指标序列。
 * @param range 财务页独立时间范围，预设范围按月计算，自定义范围按日期闭区间计算。
 * @returns 保留原指标信息并裁剪数据点后的新序列。
 */
function filterFinancialSeriesByRange(
  series: StockFinancialSeries,
  range: MarketDataRangeSelection,
): StockFinancialSeries {
  if (range.type === "custom") {
    return {
      ...series,
      points: series.points.filter(
        (point) =>
          (!range.startDate || point.period >= range.startDate) &&
          (!range.endDate || point.period <= range.endDate),
      ),
    };
  }

  const selectedOption = STOCK_RANGE_OPTIONS.find((option) => option.value === range.type);
  const latestPeriod = series.points.at(-1)?.period;
  if (!selectedOption?.months || !latestPeriod) return series;

  const latestMonth = periodMonthIndex(latestPeriod);
  if (latestMonth === null) return series;
  const cutoffMonth = latestMonth - selectedOption.months;
  return {
    ...series,
    points: series.points.filter((point) => {
      const pointMonth = periodMonthIndex(point.period);
      return pointMonth !== null && pointMonth >= cutoffMonth;
    }),
  };
}

/**
 * 将财报日期转换为连续月份序号，便于按月裁剪季度和年度序列。
 * @param period ISO 日期格式的财报期间。
 * @returns 连续月份序号；格式无效时返回 null。
 */
function periodMonthIndex(period: string): number | null {
  const year = Number(period.slice(0, 4));
  const month = Number(period.slice(5, 7));
  if (!Number.isInteger(year) || !Number.isInteger(month) || month < 1 || month > 12) return null;
  return year * 12 + month - 1;
}

function FinancialMetricCard(props: { series: StockFinancialSeries }) {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const latestPoint = props.series.points.at(-1);
  const previousPoint = props.series.points.at(-2);
  const unit = latestPoint?.unit || "亿元";
  const changeRate =
    latestPoint && previousPoint && previousPoint.value !== 0
      ? ((latestPoint.value - previousPoint.value) / Math.abs(previousPoint.value)) * 100
      : 0;
  const option = useMemo((): echarts.EChartsOption => {
    return {
      animation: false,
      legend: {
        top: 8,
        right: 16,
        data: [props.series.label],
        itemWidth: 14,
        itemHeight: 8,
        textStyle: { color: "#64748b", fontSize: 10 },
      },
      grid: { left: 64, right: 24, top: 46, bottom: 38 },
      xAxis: {
        type: "category",
        data: props.series.points.map((point) => compactPeriod(point.period)),
        axisLabel: { color: "#64748b", fontSize: 10 },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        name: unit,
        nameTextStyle: { color: "#64748b", fontSize: 10 },
        axisLabel: { color: "#64748b", fontSize: 10 },
        splitLine: { lineStyle: { color: "#eef2f7" } },
      },
      series: [
        {
          name: props.series.label,
          type: props.series.metric === "liability" ? "line" : "bar",
          smooth: true,
          symbol: props.series.metric === "liability" ? "circle" : "none",
          barWidth: 12,
          itemStyle: { color: "#3b82f6" },
          lineStyle: { color: "#3b82f6", width: 2 },
          data: props.series.points.map((point) => point.value),
        },
      ],
      tooltip: {
        trigger: "axis",
        confine: true,
        padding: [6, 8],
        textStyle: { fontSize: 10, lineHeight: 15 },
      },
    };
  }, [props.series, unit]);

  useEffect(() => {
    if (!chartRef.current) return;
    const instance = echarts.init(chartRef.current, undefined, { renderer: "svg" });
    instance.setOption(option);
    const isTestRuntime =
      typeof navigator !== "undefined" && navigator.userAgent.toLowerCase().includes("jsdom");
    const observer =
      !isTestRuntime && typeof ResizeObserver !== "undefined"
        ? new ResizeObserver(() => instance.resize())
        : null;
    observer?.observe(chartRef.current);
    return () => {
      observer?.disconnect();
      instance.dispose();
    };
  }, [option]);

  return (
    <article className="flex h-full min-h-0 flex-col overflow-hidden rounded-md border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="text-sm font-bold text-slate-900">{props.series.label}</h4>
          <div className="mt-1 text-xs font-semibold text-slate-500">单位：{unit}</div>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-slate-950">{latestPoint ? formatNumber(latestPoint.value, 2) : "--"}</div>
          <div className={`text-xs font-bold ${changeRate >= 0 ? "text-rose-500" : "text-emerald-600"}`}>
            {latestPoint && previousPoint ? `${formatSigned(changeRate, 2)}%` : "--"}
          </div>
        </div>
      </div>
      <div
        ref={chartRef}
        aria-label={`${props.series.label} 图表`}
        className="mt-2 min-h-0 w-full flex-1"
        role="img"
      />
    </article>
  );
}

function SideInfoPanel(props: { title: string; rows: Array<[string, string]>; valueTone?: boolean }) {
  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-900">{props.title}</h3>
        <button className="text-xs font-semibold text-slate-400" type="button">更多 &gt;</button>
      </div>
      <dl className="space-y-2.5 text-xs">
        {props.rows.map(([label, value]) => (
          <div className="flex items-start justify-between gap-4" key={label}>
            <dt className="whitespace-nowrap font-semibold text-slate-400">{label}</dt>
            <dd className={`text-right font-semibold text-slate-700 ${props.valueTone ? toneForValue(label, value) : ""}`}>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function EmptySurface(props: { text: string; danger?: boolean }) {
  return (
    <div className={`m-4 rounded-md border p-8 text-sm ${props.danger ? "border-rose-200 bg-rose-50 text-rose-700" : "border-slate-200 bg-white text-slate-500"}`}>
      {props.text}
    </div>
  );
}

/**
 * 根据列表内容区高度计算单页可展示的标的数量。
 * @param availableHeight 列表表头与数据行可使用的像素高度。
 * @returns 在 6 到 30 条之间的自适应分页容量。
 */
function calculateInstrumentPageSize(availableHeight: number): number {
  if (availableHeight <= INSTRUMENT_TABLE_HEADER_HEIGHT) return DEFAULT_INSTRUMENT_PAGE_SIZE;
  const visibleRows = Math.floor(
    (availableHeight - INSTRUMENT_TABLE_HEADER_HEIGHT) / INSTRUMENT_ROW_HEIGHT,
  );
  return Math.min(30, Math.max(6, visibleRows));
}

/**
 * 生成紧凑分页项，首尾页始终可达，当前页附近保留连续页码。
 * @param currentPage 当前页码。
 * @param totalPages 总页数。
 * @returns 页码与省略号标识列表。
 */
function buildPaginationItems(currentPage: number, totalPages: number): Array<number | string> {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }
  if (currentPage <= 4) {
    return [1, 2, 3, 4, 5, "ellipsis-right", totalPages];
  }
  if (currentPage >= totalPages - 3) {
    return [1, "ellipsis-left", totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
  }
  return [1, "ellipsis-left", currentPage - 1, currentPage, currentPage + 1, "ellipsis-right", totalPages];
}

function lineSeries(name: string, data: Array<number | null>, color: string) {
  return {
    name,
    type: "line" as const,
    smooth: true,
    symbol: "none",
    data,
    lineStyle: { color, width: 1.4 },
    itemStyle: { color },
  };
}

function toneForValue(label: string, value: string): string {
  if (label.includes("涨")) return value.startsWith("-") ? "text-emerald-600" : "text-rose-500";
  if (label.includes("最高")) return "text-rose-500";
  if (label.includes("最低")) return "text-emerald-600";
  return "";
}

function compactPeriod(period: string): string {
  const match = period.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return period;
  const quarterByMonth: Record<string, string> = { "03": "Q1", "06": "Q2", "09": "Q3", "12": "Q4" };
  return `${match[1]}${quarterByMonth[match[2]] ?? match[2]}`;
}

function formatNumber(value: number, digits = 0): string {
  return new Intl.NumberFormat("zh-CN", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

function formatSigned(value: number, digits = 2): string {
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${formatNumber(value, digits)}`;
}

function formatCompactNumber(value: number): string {
  if (Math.abs(value) >= 100000000) return `${formatNumber(value / 100000000, 2)}亿`;
  if (Math.abs(value) >= 10000) return `${formatNumber(value / 10000, 2)}万`;
  return formatNumber(value, 0);
}
