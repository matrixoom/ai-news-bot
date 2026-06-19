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
import { useStockMarketAllRefresh } from "../hooks/use-stock-market-all-refresh";
import { useStockMarketInstrumentsQuery } from "../hooks/use-stock-market-instruments-query";
import { useStockMarketOverviewQuery } from "../hooks/use-stock-market-overview-query";
import { useStockMarketRefreshMutation } from "../hooks/use-stock-market-refresh-mutation";
import type {
  MarketDataRangeSelection,
  StockDailyBar,
  StockFinancialReportType,
  StockFinancialSeries,
  StockMarketAllRefreshJob,
  StockInstrument,
  StockMarketOverviewPayload,
} from "../model/market-data.types";
import { formatLocalDateTime } from "../../../shared/utils/format-local-date-time";
import { buildCartesianTheme, useWorkbenchChartTheme } from "../../../shared/charts/use-workbench-chart-theme";
import { MarketOverviewStrip } from "./market-overview-strip";

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
  { value: "沪市", label: "沪市" },
  { value: "深市", label: "深市" },
  { value: "沪市主板", label: "沪市主板" },
  { value: "深市主板", label: "深市主板" },
  { value: "科创板", label: "科创板" },
  { value: "创业板", label: "创业板" },
  { value: "北交所", label: "北交所" },
  { value: "境外", label: "境外" },
];

const INSTRUMENT_TYPE_OPTIONS = [
  { value: "all", label: "全部" },
  { value: "stock", label: "股票" },
  { value: "etf", label: "ETF" },
  { value: "lof", label: "LOF" },
];

const LISTING_STATUS_OPTIONS = [
  { value: "all", label: "全部" },
  { value: "listed", label: "上市" },
  { value: "st", label: "ST" },
  { value: "delisted", label: "退市" },
];

const FINANCIAL_ORDER = [
  "revenue",
  "expense",
  "cash_flow",
  "asset",
  "liability",
  "roe",
  "revenue_yoy",
  "net_profit_yoy",
  "debt_asset_ratio",
];
const DEFAULT_INSTRUMENT_PAGE_SIZE = 18;
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
  const [isResearchSummaryCollapsed, setIsResearchSummaryCollapsed] = useState(false);
  const [activeDetailTab, setActiveDetailTab] = useState<StockDetailTab>("overview");
  const [priceAdjustment, setPriceAdjustment] = useState<StockPriceAdjustment>("none");
  const [selectedIndexSymbol, setSelectedIndexSymbol] = useState<string | null>(null);
  const [indexRange, setIndexRange] = useState<MarketDataRangeSelection>({ type: "1m" });

  const instrumentsQuery = useStockMarketInstrumentsQuery({
    query: searchText,
    instrumentType,
    marketBoard,
    listingStatus,
    page: instrumentPage,
    pageSize: instrumentPageSize,
  });
  const detailQuery = useStockMarketDetailQuery(selectedSymbol, range, financialReportType);
  const overviewQuery = useStockMarketOverviewQuery();
  const refreshMutation = useStockMarketRefreshMutation(selectedSymbol, range, financialReportType);
  const allRefresh = useStockMarketAllRefresh();
  const instruments = instrumentsQuery.data?.items ?? [];
  const instrumentTotal = instrumentsQuery.data?.total ?? 0;
  const instrumentPageCount = Math.max(1, Math.ceil(instrumentTotal / instrumentPageSize));
  const selectedOverviewIndex = useMemo(
    () => overviewQuery.data?.indices.find((index) => index.symbol === selectedIndexSymbol) ?? null,
    [overviewQuery.data?.indices, selectedIndexSymbol],
  );

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

  /** 切换顶部宽基指数展开图，重复点击当前指数时收起。 */
  function handleOverviewIndexSelect(symbol: string) {
    setSelectedIndexSymbol((current) => (current === symbol ? null : symbol));
  }

  return (
    <div className="-m-4 flex min-h-[calc(100vh-4.5rem)] flex-col overflow-hidden bg-canvas text-ink md:-m-6">
      <MarketOverviewStrip
        data={overviewQuery.data}
        error={overviewQuery.isError}
        onIndexSelect={handleOverviewIndexSelect}
        pending={overviewQuery.isPending}
        selectedIndexSymbol={selectedIndexSymbol}
      />
      {selectedOverviewIndex ? (
        <IndexKlineDisclosure
          index={selectedOverviewIndex}
          onRangeChange={setIndexRange}
          range={indexRange}
        />
      ) : (
        <>
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
            className={`grid min-h-[42rem] flex-1 grid-cols-1 items-stretch gap-3 overflow-hidden p-3 ${
              isInstrumentListCollapsed
                ? "xl:grid-cols-[48px_minmax(0,1fr)]"
                : "xl:grid-cols-[360px_minmax(0,1fr)]"
            }`}
          >
            <InstrumentListPanel
              currentPage={instrumentPage}
              instruments={instruments}
              isCollapsed={isInstrumentListCollapsed}
              isError={instrumentsQuery.isError}
              isPending={instrumentsQuery.isPending}
              allRefreshJob={allRefresh.job}
              allRefreshError={allRefresh.errorMessage}
              allRefreshStarting={allRefresh.isStarting}
              onCollapseChange={setIsInstrumentListCollapsed}
              onRefreshAll={allRefresh.start}
              onPageChange={setInstrumentPage}
              onPageSizeChange={handleInstrumentPageSizeChange}
              onSelect={setSelectedSymbol}
              pageSize={instrumentPageSize}
              selectedSymbol={selectedSymbol}
              total={instrumentTotal}
              warning={instrumentsQuery.data?.warning_message ?? ""}
            />

            <section
              className="workbench-panel flex h-full min-h-0 min-w-0 flex-col overflow-hidden"
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
                      className={`grid min-h-0 flex-1 gap-3 p-3 ${
                        isResearchSummaryCollapsed
                          ? "lg:grid-cols-[minmax(0,1fr)_44px]"
                          : "lg:grid-cols-[minmax(0,1fr)_260px]"
                      }`}
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
                      <ResearchSummaryPanel
                        bars={detailQuery.data?.daily_bars ?? []}
                        companySummary={detailQuery.data?.profile.summary ?? ""}
                        industry={detailQuery.data?.profile.industry ?? ""}
                        isCollapsed={isResearchSummaryCollapsed}
                        onCollapseChange={setIsResearchSummaryCollapsed}
                        syncedAt={detailQuery.data?.sync_state.synced_at ?? ""}
                      />
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
        </>
      )}
    </div>
  );
}

/** 渲染顶部宽基指数的下发展开 K 线面板。 */
function IndexKlineDisclosure(props: {
  index: StockMarketOverviewPayload["indices"][number];
  range: MarketDataRangeSelection;
  onRangeChange: (range: MarketDataRangeSelection) => void;
}) {
  const bars = props.index.daily_bars ?? [];
  const visibleBars = useMemo(() => filterDailyBarsByRange(bars, props.range), [bars, props.range]);
  const latest = bars.at(-1);
  const rangeChangeRate = calculateRangeChangeRate(visibleBars);
  const rangeChangeTone =
    rangeChangeRate === null || rangeChangeRate === 0
      ? "text-muted"
      : rangeChangeRate > 0
        ? "text-positive"
        : "text-negative";

  return (
    <div className="min-h-[42rem] flex-1 overflow-hidden p-3">
      <section
        aria-label={`${props.index.display_name} 宽基指数K线`}
        className="workbench-panel flex h-full min-h-0 flex-col overflow-hidden p-4"
      >
        <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-ink">{props.index.display_name} K线</h2>
            <p className="mt-1 text-xs font-medium text-muted">
              Push Center 历史 · {latest?.date ?? props.index.trade_date ?? "--"}
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-3 text-xs font-semibold">
            <span
              aria-label={`${props.index.display_name} 当前时间跨度涨幅`}
              className="text-ink"
            >
              区间涨幅{" "}
              <span className={rangeChangeTone}>
                {rangeChangeRate === null ? "--" : `${formatSigned(rangeChangeRate, 2)}%`}
              </span>
            </span>
            <span className="text-muted">{props.index.symbol}</span>
          </div>
        </div>
        <IndexRangeToolbar
          bars={bars}
          onRangeChange={props.onRangeChange}
          range={props.range}
        />
        <KlinePanel
          bars={visibleBars}
          chartMode="index"
          isError={false}
          isPending={false}
          symbol={props.index.symbol}
          warning="当前宽基指数暂无可展示历史。"
        />
      </section>
    </div>
  );
}

/** 渲染宽基指数 K 线的时间范围控件，选项与股票行情保持一致。 */
function IndexRangeToolbar(props: {
  bars: StockDailyBar[];
  range: MarketDataRangeSelection;
  onRangeChange: (range: MarketDataRangeSelection) => void;
}) {
  const firstDate = props.bars[0]?.date ?? "";
  const latestDate = props.bars.at(-1)?.date ?? "";
  const [startDate, setStartDate] = useState(props.range.startDate ?? firstDate);
  const [endDate, setEndDate] = useState(props.range.endDate ?? latestDate);

  return (
    <div className="mb-3 flex shrink-0 flex-wrap items-center gap-2">
      <div
        aria-label="宽基指数时间范围"
        className="inline-flex h-8 overflow-hidden rounded-control border border-line bg-surface"
      >
        {STOCK_RANGE_OPTIONS.map((option) => (
          <button
            aria-pressed={props.range.type === option.value}
            className={`border-r border-line px-3 text-xs font-semibold last:border-r-0 ${
              props.range.type === option.value ? "bg-accent text-white" : "text-muted hover:bg-accent-soft hover:text-accent"
            }`}
            key={option.value}
            onClick={() =>
              props.onRangeChange(
                option.value === "custom"
                  ? { type: "custom", startDate: startDate || firstDate, endDate: endDate || latestDate }
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
        <label className="inline-flex h-10 items-center gap-2 rounded-control border border-line bg-surface px-3 text-sm font-semibold text-muted">
          <input
            aria-label="宽基指数起始日期"
            className="w-28 bg-transparent text-ink outline-none"
            onChange={(event) => {
              setStartDate(event.target.value);
              props.onRangeChange({ type: "custom", startDate: event.target.value, endDate });
            }}
            type="date"
            value={startDate}
          />
          <span>至</span>
          <input
            aria-label="宽基指数结束日期"
            className="w-28 bg-transparent text-ink outline-none"
            onChange={(event) => {
              setEndDate(event.target.value);
              props.onRangeChange({ type: "custom", startDate, endDate: event.target.value });
            }}
            type="date"
            value={endDate}
          />
          <CalendarDaysIcon aria-hidden="true" className="h-4 w-4 text-muted" />
        </label>
      ) : null}
    </div>
  );
}

/** 渲染所选标的的基础研究摘要与关键行情指标。 */
function ResearchSummaryPanel(props: {
  bars: StockDailyBar[];
  companySummary: string;
  industry: string;
  isCollapsed: boolean;
  onCollapseChange: (collapsed: boolean) => void;
  syncedAt: string;
}) {
  const latest = props.bars.at(-1);
  const previous = props.bars.at(-2);
  const changeRate =
    latest && previous && previous.close !== 0
      ? ((latest.close - previous.close) / previous.close) * 100
      : null;
  const rangeChangeRate = calculateRangeChangeRate(props.bars);
  const rangeChangeTone =
    rangeChangeRate === null || rangeChangeRate === 0
      ? "text-muted"
      : rangeChangeRate > 0
        ? "text-positive"
        : "text-negative";
  const direction = changeRate === null || changeRate === 0 ? "平盘" : changeRate > 0 ? "上涨" : "下跌";
  const directionTone =
    changeRate === null || changeRate === 0 ? "text-muted" : changeRate > 0 ? "text-positive" : "text-negative";

  if (props.isCollapsed) {
    return (
      <aside
        aria-label="研究摘要"
        className="flex min-h-0 items-start justify-center border-t border-line pt-3 lg:border-l lg:border-t-0 lg:pt-3"
      >
        <button
          aria-expanded="false"
          aria-label="展开研究摘要"
          className="workbench-icon-button h-8 w-8"
          onClick={() => props.onCollapseChange(false)}
          type="button"
        >
          <ChevronLeftIcon aria-hidden="true" className="h-4 w-4" />
        </button>
      </aside>
    );
  }

  return (
    <aside aria-label="研究摘要" className="min-h-0 overflow-y-auto border-t border-line pt-3 lg:border-l lg:border-t-0 lg:pl-4 lg:pt-0">
      <div className="flex items-center justify-between gap-2">
        <p className="workbench-kicker">研究摘要</p>
        <button
          aria-expanded="true"
          aria-label="折叠研究摘要"
          className="workbench-icon-button h-8 w-8 border-transparent"
          onClick={() => props.onCollapseChange(true)}
          type="button"
        >
          <ChevronRightIcon aria-hidden="true" className="h-4 w-4" />
        </button>
      </div>
      <h3 className="mt-2 text-base font-semibold text-ink">{props.industry || "基础行情观察"}</h3>
      <p className="mt-2 text-sm leading-6 text-muted">
        {props.companySummary || "基于当前选择窗口展示价格趋势、成交量与估值指标，供进一步研究核验。"}
      </p>
      <dl className="mt-4 divide-y divide-line border-y border-line">
        <SummaryRow label="最新收盘" value={latest ? formatNumber(latest.close, 2) : "--"} />
        <SummaryRow
          label="当日方向"
          tone={directionTone}
          value={changeRate === null ? "--" : `${direction} ${formatSigned(changeRate, 2)}%`}
        />
        <SummaryRow label="成交量" value={latest ? formatCompactNumber(latest.volume) : "--"} />
        <SummaryRow label="市盈率 TTM" value={latest?.pe_ttm === null || latest?.pe_ttm === undefined ? "--" : formatNumber(latest.pe_ttm, 2)} />
        <SummaryRow label="市净率 MRQ" value={latest?.pb_mrq === null || latest?.pb_mrq === undefined ? "--" : formatNumber(latest.pb_mrq, 2)} />
        <SummaryRow
          label="总市值"
          value={latest?.total_market_cap === null || latest?.total_market_cap === undefined ? "--" : `${formatNumber(latest.total_market_cap, 2)}亿`}
        />
        <SummaryRow
          label="区间涨幅"
          tone={rangeChangeTone}
          value={rangeChangeRate === null ? "--" : `${formatSigned(rangeChangeRate, 2)}%`}
        />
      </dl>
      <p className="mt-3 text-[11px] leading-5 text-muted">
        数据更新时间：{props.syncedAt ? formatLocalDateTime(props.syncedAt) : "尚未记录"}
      </p>
    </aside>
  );
}

/** 渲染研究摘要中的单项键值。 */
function SummaryRow(props: { label: string; value: string; tone?: string }) {
  return (
    <div className="flex items-center justify-between gap-3 py-2.5 text-xs">
      <dt className="text-muted">{props.label}</dt>
      <dd className={`text-right font-semibold ${props.tone ?? "text-ink"}`}>{props.value}</dd>
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
    <div className="flex flex-wrap items-center gap-3 border-b border-line bg-surface px-4 py-3">
      <div className="flex h-10 w-full max-w-[320px] items-center gap-2 rounded-control border border-line bg-surface px-3 text-sm">
        <input
          className="min-w-0 flex-1 bg-transparent text-ink outline-none placeholder:text-muted"
          onChange={(event) => props.onSearchTextChange(event.target.value)}
          placeholder="搜索股票代码 / 名称"
          type="search"
          value={props.searchText}
        />
        <MagnifyingGlassIcon aria-hidden="true" className="h-5 w-5 text-muted" />
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
    <label className="flex items-center gap-2 text-xs font-semibold text-muted">
      {props.label}
      <select
        className="workbench-input min-w-32 font-medium"
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
  allRefreshJob: StockMarketAllRefreshJob | null;
  allRefreshError: string;
  allRefreshStarting: boolean;
  warning: string;
  onSelect: (symbol: string) => void;
  onRefreshAll: () => void;
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
        className="workbench-panel flex h-full min-h-0 items-start justify-center pt-5"
        data-testid="instrument-list-panel"
      >
        <button
          aria-expanded="false"
          aria-label="展开股票列表"
          className="workbench-icon-button h-8 w-8"
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
      className="workbench-panel flex h-full min-h-0 flex-col overflow-hidden"
      data-testid="instrument-list-panel"
    >
      <div className="flex h-12 items-center justify-between gap-2 border-b border-line px-4">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <button
            aria-label="刷新全部标的数据"
            className="workbench-icon-button h-8 w-8 shrink-0 disabled:cursor-not-allowed disabled:opacity-40"
            disabled={props.allRefreshStarting}
            onClick={props.onRefreshAll}
            title="后台刷新全部标的近 6 个月行情、公司概况和财务数据；本地已覆盖的标的会跳过外部请求"
            type="button"
          >
            <ArrowPathIcon
              aria-hidden="true"
              className={`h-4 w-4 ${props.allRefreshStarting || isAllRefreshRunning(props.allRefreshJob) ? "animate-spin" : ""}`}
            />
          </button>
          <div className="min-w-0 text-sm font-semibold text-ink">
            全部标的
            <span className="ml-3 text-xs font-medium text-muted">{formatNumber(props.total)} 只</span>
          </div>
          {props.allRefreshError ? (
            <AllInstrumentRefreshError message={props.allRefreshError} />
          ) : (
            <AllInstrumentRefreshProgress job={props.allRefreshJob} />
          )}
        </div>
        <button
          aria-expanded="true"
          aria-label="折叠股票列表"
          className="workbench-icon-button h-8 w-8 border-transparent"
          onClick={() => props.onCollapseChange(true)}
          type="button"
        >
          <ChevronLeftIcon aria-hidden="true" className="h-4 w-4" />
        </button>
      </div>
      <div
        className="min-h-0 flex-1 overflow-x-auto overflow-y-hidden"
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
          <table className="min-w-[420px] w-full table-fixed border-collapse text-left text-xs">
            <thead className="sticky top-0 z-10 bg-surface-subtle text-muted">
              <tr className="border-b border-line">
                <th className="w-[96px] px-4 py-2.5 font-semibold">代码</th>
                <th className="px-3 py-2.5 font-semibold">名称</th>
                <th className="w-[80px] px-3 py-2.5 font-semibold">市场</th>
                <th className="w-[58px] px-3 py-2.5 font-semibold">类型</th>
                <th className="w-[72px] px-4 py-2.5 text-right font-semibold">最新价</th>
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
        className="flex h-12 shrink-0 items-center gap-2 border-t border-line px-3 text-xs text-muted"
      >
        <button
          aria-label="上一页"
          className="workbench-icon-button h-7 w-7 disabled:cursor-not-allowed disabled:opacity-40"
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
                  ? "bg-accent text-white"
                  : "text-muted hover:bg-accent-soft hover:text-accent"
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
          className="workbench-icon-button h-7 w-7 disabled:cursor-not-allowed disabled:opacity-40"
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
 * 渲染全部标的刷新启动失败提示。
 * @param props.message 失败原因，用于悬停定位具体 HTTP 或网络错误。
 * @returns 列表标题行内的紧凑错误提示。
 */
function AllInstrumentRefreshError(props: { message: string }) {
  return (
    <div
      aria-label="全部标的刷新错误"
      className="hidden max-w-28 shrink-0 truncate text-[10px] font-semibold text-negative sm:block"
      role="status"
      title={props.message}
    >
      全部刷新启动失败
    </div>
  );
}

/**
 * 渲染全部标的后台刷新微型进度条。
 * @param props.job 后端刷新任务；为空时保留一个窄占位，避免标题跳动。
 * @returns 列表标题行内的紧凑进度展示。
 */
function AllInstrumentRefreshProgress(props: { job: StockMarketAllRefreshJob | null }) {
  if (!props.job) {
    return <div className="hidden h-5 w-24 shrink-0 sm:block" />;
  }

  const percentage = Math.min(100, Math.max(0, props.job.percentage));
  const isFailed = props.job.status === "failed";
  const isWarning = props.job.status === "completed_with_warnings";
  const barTone = isFailed ? "bg-negative" : isWarning ? "bg-amber-500" : "bg-accent";

  return (
    <div
      aria-label="全部标的刷新进度"
      aria-valuemax={100}
      aria-valuemin={0}
      aria-valuenow={percentage}
      className="hidden w-24 shrink-0 sm:block"
      role="progressbar"
      title={props.job.message}
    >
      <div className="h-1.5 overflow-hidden rounded-full bg-surface-subtle">
        <div className={`h-full rounded-full ${barTone}`} style={{ width: `${percentage}%` }} />
      </div>
      <div className="mt-0.5 truncate text-[10px] font-semibold leading-3 text-muted">
        {formatNumber(props.job.completed)}/{formatNumber(props.job.total)}
      </div>
    </div>
  );
}

/**
 * 判断全部标的刷新任务是否仍在后台运行。
 * @param job 后端刷新任务状态。
 * @returns pending/running 时返回 true。
 */
function isAllRefreshRunning(job: StockMarketAllRefreshJob | null): boolean {
  return job?.status === "pending" || job?.status === "running";
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
  const priceTone = latestPrice === undefined || latestPrice === null ? "text-muted" : "text-positive";
  const marketLabel = props.instrument.market_board.replace("主板", "");
  const typeLabel =
    props.instrument.instrument_type === "etf"
      ? "ETF"
      : props.instrument.instrument_type === "lof"
        ? "LOF"
        : "股票";
  const latestPriceLabel = latestPrice === undefined || latestPrice === null ? "--" : formatNumber(latestPrice, 3);
  const hoverDescription = `代码：${props.instrument.symbol}；名称：${props.instrument.name}；市场：${marketLabel}；类型：${typeLabel}；最新价：${latestPriceLabel}`;
  return (
    <tr
      className={`cursor-pointer border-b border-line text-ink hover:bg-accent-soft/60 ${
        props.selected ? "bg-accent-soft" : ""
      }`}
      onClick={() => props.onSelect(props.instrument.symbol)}
      title={hoverDescription}
    >
      <td className="px-4 py-1.5 font-semibold">{props.instrument.symbol}</td>
      <td className="truncate px-3 py-1.5 font-semibold text-ink">{props.instrument.name}</td>
      <td className="px-3 py-1.5 text-muted">{marketLabel}</td>
      <td className="px-3 py-1.5 text-muted">{typeLabel}</td>
      <td className={`px-4 py-1.5 text-right font-semibold ${priceTone}`}>
        {latestPriceLabel}
      </td>
    </tr>
  );
}

function StockSummaryHeader(props: { instrument: StockInstrument }) {
  return (
    <header className="px-5 pb-3 pt-4">
      <div className="min-w-[320px]">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-xl font-semibold tracking-tight text-ink">
            {props.instrument.symbol}
            <span className="ml-4">{props.instrument.name}</span>
          </h2>
          <span className="rounded-control bg-accent-soft px-2.5 py-1 text-xs font-semibold text-accent">{props.instrument.market_board}</span>
        </div>
        <div className="mt-1 text-xs font-medium text-muted">{props.instrument.name}股份有限公司</div>
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
    <div aria-label="股票详情" className="flex h-11 items-end gap-7 border-b border-line px-5" role="tablist">
      {tabs.map((tab) => {
        const isActive = props.activeTab === tab.value;
        return (
          <button
            aria-controls={`stock-detail-panel-${tab.value}`}
            aria-selected={isActive}
            className={`relative h-11 px-1 text-sm font-semibold ${
              isActive ? "text-accent" : "text-muted hover:text-ink"
            }`}
            id={`stock-detail-tab-${tab.value}`}
            key={tab.value}
            onClick={() => props.onTabChange(tab.value)}
            role="tab"
            type="button"
          >
            {tab.label}
            {isActive ? <span className="absolute inset-x-0 bottom-0 h-0.5 rounded-full bg-accent" /> : null}
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
        className="inline-flex h-8 overflow-hidden rounded-control border border-line bg-surface"
      >
        {STOCK_RANGE_OPTIONS.map((option) => (
          <button
            aria-pressed={props.range.type === option.value}
            className={`border-r border-line px-3 text-xs font-semibold last:border-r-0 ${
              props.range.type === option.value ? "bg-accent text-white" : "text-muted hover:bg-accent-soft hover:text-accent"
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
        <label className="inline-flex h-10 items-center gap-2 rounded-control border border-line bg-surface px-3 text-sm font-semibold text-muted">
          <input
            aria-label="起始日期"
            className="w-28 bg-transparent text-ink outline-none"
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
            className="w-28 bg-transparent text-ink outline-none"
            onChange={(event) => {
              setEndDate(event.target.value);
              props.onRangeChange({ type: "custom", startDate, endDate: event.target.value });
            }}
            type="date"
            value={endDate}
          />
          <CalendarDaysIcon aria-hidden="true" className="h-4 w-4 text-muted" />
        </label>
      ) : null}
      <div className="ml-auto flex items-center gap-2">
        <button
          aria-label="刷新行情数据"
          className="workbench-icon-button h-8 w-8 disabled:cursor-not-allowed disabled:opacity-40"
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
          className="inline-flex h-8 overflow-hidden rounded-control border border-line bg-surface text-xs font-semibold"
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
                className={`border-r border-line px-3 last:border-r-0 ${
                  isSelected
                    ? "bg-accent text-white"
                    : "text-muted hover:bg-accent-soft hover:text-accent"
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
  chartMode?: "stock" | "index";
}) {
  if (props.isPending) return <EmptySurface text="行情数据加载中..." />;
  if (props.isError) return <EmptySurface danger text="行情数据加载失败。" />;
  if (props.bars.length === 0) return <EmptySurface text={props.warning || "当前时间范围暂无行情数据。"} />;
  return (
    <section className="flex min-h-0 flex-1 border-b border-line bg-surface pb-2">
      <KlineChart bars={props.bars} mode={props.chartMode ?? "stock"} symbol={props.symbol} />
    </section>
  );
}

function KlineChart(props: { bars: StockDailyBar[]; mode?: "stock" | "index"; symbol: string }) {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const workbenchTheme = useWorkbenchChartTheme();
  const chartTheme = useMemo(() => buildCartesianTheme(workbenchTheme), [workbenchTheme]);
  const option = useMemo((): echarts.EChartsOption => {
    const labels = props.bars.map((bar) => bar.date);
    const isIndexChart = props.mode === "index";
    const legendData = isIndexChart
      ? ["MA5", "MA10", "MA20", "MA60", "MA120"]
      : ["K线", "MA5", "MA10", "MA20", "MA60", "MA120"];
    return {
      animation: false,
      tooltip: {
        trigger: "axis",
        confine: true,
        padding: [6, 8],
        ...chartTheme.tooltip,
        textStyle: { fontSize: 10, lineHeight: 15 },
        axisPointer: { type: "cross" },
      },
      legend: {
        top: 8,
        right: 8,
        bottom: 32,
        orient: "vertical",
        type: "scroll",
        itemWidth: 16,
        itemHeight: 8,
        textStyle: chartTheme.legendText,
        data: legendData,
        selected: {},
      },
      grid: [
        { left: 54, right: 112, top: 38, height: "56%" },
        { left: 54, right: 112, top: "70%", height: "14%" },
      ],
      xAxis: [
        {
          type: "category",
          data: labels,
          boundaryGap: true,
          ...chartTheme.categoryAxis,
        },
        {
          type: "category",
          data: labels,
          gridIndex: 1,
          boundaryGap: true,
          ...chartTheme.categoryAxis,
        },
      ],
      yAxis: [
        {
          type: "value",
          scale: true,
          ...chartTheme.valueAxis,
        },
        {
          type: "value",
          gridIndex: 1,
          axisLabel: { show: false },
          axisTick: { show: false },
          axisLine: { show: false },
          splitLine: chartTheme.valueAxis.splitLine,
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
          itemStyle: {
            color: workbenchTheme.positive,
            color0: workbenchTheme.negative,
            borderColor: workbenchTheme.positive,
            borderColor0: workbenchTheme.negative,
          },
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
              return bar.close >= bar.open ? workbenchTheme.positive : workbenchTheme.negative;
            },
          },
        },
      ],
    };
  }, [props.bars, props.mode, chartTheme, workbenchTheme]);

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
          className="flex h-10 shrink-0 items-end gap-7 border-b border-line"
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
                    ? "border-accent text-accent"
                    : "border-transparent text-muted hover:text-ink"
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
        className="flex shrink-0 flex-wrap items-center gap-2 border-b border-line pb-3"
      >
        {/*<span className="text-xs font-semibold text-slate-500">时间范围</span>*/}
        <div aria-label="财务时间范围" className="inline-flex h-8 overflow-hidden rounded-control border border-line bg-surface">
          {STOCK_RANGE_OPTIONS.map((option) => (
            <button
              aria-pressed={props.financialRange.type === option.value}
              className={`border-r border-line px-3 text-xs font-semibold last:border-r-0 ${
                props.financialRange.type === option.value
                  ? "bg-accent text-white"
                  : "text-muted hover:bg-accent-soft hover:text-accent"
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
          <label className="inline-flex h-8 items-center gap-2 rounded-control border border-line bg-surface px-3 text-xs font-semibold text-muted">
            <input
              aria-label="财务起始日期"
              className="w-28 bg-transparent text-ink outline-none"
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
              className="w-28 bg-transparent text-ink outline-none"
              onChange={(event) =>
                props.onFinancialRangeChange({
                  ...props.financialRange,
                  endDate: event.target.value,
                })
              }
              type="date"
              value={props.financialRange.endDate ?? ""}
            />
            <CalendarDaysIcon aria-hidden="true" className="h-4 w-4 text-muted" />
          </label>
        ) : null}
        <div
          aria-label="财报周期"
          className="ml-auto inline-flex h-8 overflow-hidden rounded-control border border-line bg-surface text-xs font-semibold"
        >
          {(["quarterly", "yearly"] as const).map((type) => (
            <button
              aria-pressed={props.reportType === type}
              className={`px-4 ${
                props.reportType === type
                  ? "bg-accent text-white"
                  : "text-muted hover:bg-accent-soft hover:text-accent"
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
 * 按行情时间范围裁剪日线序列，预设范围使用序列最新交易日作为终点。
 * @param bars 原始日线序列。
 * @param range 行情时间范围。
 * @returns 裁剪后的日线序列。
 */
function filterDailyBarsByRange(
  bars: StockDailyBar[],
  range: MarketDataRangeSelection,
): StockDailyBar[] {
  if (range.type === "custom") {
    return bars.filter(
      (bar) =>
        (!range.startDate || bar.date >= range.startDate) &&
        (!range.endDate || bar.date <= range.endDate),
    );
  }

  const selectedOption = STOCK_RANGE_OPTIONS.find((option) => option.value === range.type);
  const latestDate = bars.at(-1)?.date;
  if (!selectedOption?.months || !latestDate) return bars;

  const cutoffDate = shiftIsoDateByMonths(latestDate, -selectedOption.months);
  if (!cutoffDate) return bars;
  return bars.filter((bar) => bar.date >= cutoffDate);
}

/**
 * 计算当前可见日线首尾收盘价的区间涨幅。
 * @param bars 已按时间范围裁剪后的日线序列。
 * @returns 区间涨幅百分比；数据不足或起点为 0 时返回 null。
 */
function calculateRangeChangeRate(bars: StockDailyBar[]): number | null {
  const firstBar = bars[0];
  const latestBar = bars.at(-1);
  if (!firstBar || !latestBar || firstBar.close === 0) return null;
  return ((latestBar.close - firstBar.close) / Math.abs(firstBar.close)) * 100;
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

/**
 * 将 ISO 日期按月份偏移，月底日期会收敛到目标月份最后一天。
 * @param isoDate ISO 日期字符串。
 * @param months 月份偏移量。
 * @returns 偏移后的 ISO 日期；输入无效时返回 null。
 */
function shiftIsoDateByMonths(isoDate: string, months: number): string | null {
  const year = Number(isoDate.slice(0, 4));
  const month = Number(isoDate.slice(5, 7));
  const day = Number(isoDate.slice(8, 10));
  if (!Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day)) return null;
  if (month < 1 || month > 12 || day < 1 || day > 31) return null;

  const monthIndex = month - 1 + months;
  const targetYear = year + Math.floor(monthIndex / 12);
  const targetMonthIndex = ((monthIndex % 12) + 12) % 12;
  const targetMonth = targetMonthIndex + 1;
  const lastDay = new Date(targetYear, targetMonth, 0).getDate();
  const targetDay = Math.min(day, lastDay);
  return `${targetYear}-${String(targetMonth).padStart(2, "0")}-${String(targetDay).padStart(2, "0")}`;
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
  const usesLineChart = unit === "%" || props.series.metric === "liability";
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
          type: usesLineChart ? "line" : "bar",
          smooth: true,
          symbol: usesLineChart ? "circle" : "none",
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
  }, [props.series, unit, usesLineChart]);

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
    <article className="workbench-panel flex h-full min-h-0 flex-col overflow-hidden p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="text-sm font-bold text-slate-900">{props.series.label}</h4>
          <div className="mt-1 text-xs font-semibold text-slate-500">单位：{unit}</div>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-ink">{latestPoint ? formatNumber(latestPoint.value, 2) : "--"}</div>
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
    <section className="workbench-panel p-4">
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
    <div className={`m-4 rounded-control border p-8 text-sm ${props.danger ? "border-negative/30 bg-negative/5 text-negative" : "border-line bg-surface text-muted"}`}>
      {props.text}
    </div>
  );
}

/**
 * 根据列表内容区高度计算单页可展示的标的数量。
 * @param availableHeight 列表表头与数据行可使用的像素高度。
 * @returns 最多 15 条的分页容量，保持“全部标的”列表每页固定为 15 支。
 */
function calculateInstrumentPageSize(availableHeight: number): number {
  void availableHeight;
  return DEFAULT_INSTRUMENT_PAGE_SIZE;
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
