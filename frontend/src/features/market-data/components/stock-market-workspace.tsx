import * as echarts from "echarts";
import {
  ArrowPathIcon,
  CalendarDaysIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  MagnifyingGlassIcon,
  StarIcon,
} from "@heroicons/react/24/outline";
import { useEffect, useMemo, useRef, useState } from "react";
import { useStockMarketDetailQuery } from "../hooks/use-stock-market-detail-query";
import { useStockMarketInstrumentsQuery } from "../hooks/use-stock-market-instruments-query";
import { useStockMarketRefreshMutation } from "../hooks/use-stock-market-refresh-mutation";
import { useStockMarketUniverseSyncMutation } from "../hooks/use-stock-market-universe-sync-mutation";
import type {
  MarketDataRangeSelection,
  StockDailyBar,
  StockFinancialReportType,
  StockFinancialSeries,
  StockInstrument,
} from "../model/market-data.types";
import { formatLocalDateTime } from "../../../shared/utils/format-local-date-time";

const STOCK_RANGE_OPTIONS = [
  { value: "1m", label: "近1月" },
  { value: "3m", label: "近3月" },
  { value: "6m", label: "近6月" },
  { value: "1y", label: "近1年" },
  { value: "3y", label: "近3年" },
  { value: "5y", label: "近5年" },
  { value: "custom", label: "自定义" },
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

const DETAIL_TABS = ["概览", "公司概况", "所属板块", "股票属性", "财务数据", "新闻公告"];
const FINANCIAL_ORDER = ["revenue", "expense", "cash_flow", "asset", "liability"];

/**
 * 渲染股票市场页，布局对齐截图中的交易终端式信息密度。
 */
export function StockMarketWorkspace() {
  const [searchText, setSearchText] = useState("");
  const [instrumentType, setInstrumentType] = useState("all");
  const [marketBoard, setMarketBoard] = useState("all");
  const [listingStatus, setListingStatus] = useState("all");
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [range, setRange] = useState<MarketDataRangeSelection>({ type: "3m" });
  const [financialReportType, setFinancialReportType] = useState<StockFinancialReportType>("quarterly");

  const instrumentsQuery = useStockMarketInstrumentsQuery({
    query: searchText,
    instrumentType,
    marketBoard,
    listingStatus,
  });
  const universeMutation = useStockMarketUniverseSyncMutation();
  const detailQuery = useStockMarketDetailQuery(selectedSymbol, range, financialReportType);
  const refreshMutation = useStockMarketRefreshMutation(selectedSymbol, range, financialReportType);
  const instruments = instrumentsQuery.data?.items ?? [];

  useEffect(() => {
    if (selectedSymbol || instruments.length === 0) return;
    setSelectedSymbol(instruments[0].symbol);
  }, [instruments, selectedSymbol]);

  const selectedInstrument = useMemo(
    () => instruments.find((item) => item.symbol === selectedSymbol) ?? detailQuery.data?.instrument ?? null,
    [detailQuery.data?.instrument, instruments, selectedSymbol],
  );
  const latestBar = detailQuery.data?.daily_bars.at(-1) ?? null;
  const previousBar = detailQuery.data?.daily_bars.at(-2) ?? null;
  const priceChange = latestBar && previousBar ? latestBar.close - previousBar.close : 0;
  const priceChangeRate = latestBar && previousBar && previousBar.close !== 0 ? (priceChange / previousBar.close) * 100 : 0;

  return (
    <div className="-m-8 min-h-[calc(100vh-5.75rem)] bg-[#f5f7fb] text-slate-700">
      <HeaderBand />
      <FilterBand
        instrumentType={instrumentType}
        listingStatus={listingStatus}
        marketBoard={marketBoard}
        onInstrumentTypeChange={setInstrumentType}
        onListingStatusChange={setListingStatus}
        onMarketBoardChange={setMarketBoard}
        onSearchTextChange={setSearchText}
        onSyncUniverse={() => universeMutation.mutate()}
        searchText={searchText}
        syncPending={universeMutation.isPending}
      />

      <div className="grid min-h-[calc(100vh-11.25rem)] grid-cols-1 gap-2 border-t border-slate-200 px-0 py-2 xl:grid-cols-[384px_minmax(0,1fr)]">
        <InstrumentListPanel
          instruments={instruments}
          isError={instrumentsQuery.isError}
          isPending={instrumentsQuery.isPending}
          onSelect={setSelectedSymbol}
          selectedSymbol={selectedSymbol}
          total={instrumentsQuery.data?.total ?? 0}
          warning={instrumentsQuery.data?.warning_message ?? ""}
        />

        <section className="min-w-0 bg-white">
          {selectedInstrument ? (
            <>
              <StockSummaryHeader
                instrument={selectedInstrument}
                latestBar={latestBar}
                previousBar={previousBar}
                priceChange={priceChange}
                priceChangeRate={priceChangeRate}
              />
              <DetailTabs />
              <div className="grid gap-3 border-t border-slate-100 p-3 xl:grid-cols-[minmax(0,1fr)_304px]">
                <main className="min-w-0">
                  <RangeToolbar
                    endDate={range.endDate}
                    onRangeChange={setRange}
                    onRefresh={() => refreshMutation.mutate()}
                    range={range}
                    refreshPending={refreshMutation.isPending}
                    startDate={range.startDate}
                  />
                  <DailyQuoteLine bars={detailQuery.data?.daily_bars ?? []} latestBar={latestBar} previousBar={previousBar} />
                  <KlinePanel
                    bars={detailQuery.data?.daily_bars ?? []}
                    isError={detailQuery.isError}
                    isPending={detailQuery.isPending}
                    symbol={selectedInstrument.symbol}
                    warning={detailQuery.data?.sync_state.warning_message ?? ""}
                  />
                  <FinancialCards
                    isPending={detailQuery.isPending}
                    onReportTypeChange={setFinancialReportType}
                    reportType={financialReportType}
                    series={detailQuery.data?.financials.series ?? []}
                  />
                </main>

                <aside className="space-y-3">
                  <SideInfoPanel
                    title="基础信息"
                    rows={[
                      ["股票代码", selectedInstrument.symbol],
                      ["所属交易所", selectedInstrument.exchange === "SH" ? "上海证券交易所" : selectedInstrument.exchange === "SZ" ? "深圳证券交易所" : "北京证券交易所"],
                      ["上市日期", detailQuery.data?.profile.listing_date || "--"],
                      ["所属板块", detailQuery.data?.profile.sector || selectedInstrument.market_board],
                      ["行业", detailQuery.data?.profile.industry || "--"],
                      ["地区", detailQuery.data?.profile.region || "--"],
                    ]}
                  />
                  <SideInfoPanel
                    title="行情数据"
                    rows={[
                      ["最新价", latestBar ? formatNumber(latestBar.close, 2) : "--"],
                      ["涨跌额", latestBar ? formatSigned(priceChange, 2) : "--"],
                      ["涨跌幅", latestBar ? `${formatSigned(priceChangeRate, 2)}%` : "--"],
                      ["成交量", latestBar ? formatCompactNumber(latestBar.volume) : "--"],
                      ["最高价", latestBar ? formatNumber(latestBar.high, 2) : "--"],
                      ["最低价", latestBar ? formatNumber(latestBar.low, 2) : "--"],
                      ["同步时间", detailQuery.data?.sync_state.synced_at ? formatLocalDateTime(detailQuery.data.sync_state.synced_at) : "--"],
                    ]}
                    valueTone
                  />
                </aside>
              </div>
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
  syncPending: boolean;
  onSearchTextChange: (value: string) => void;
  onInstrumentTypeChange: (value: string) => void;
  onMarketBoardChange: (value: string) => void;
  onListingStatusChange: (value: string) => void;
  onSyncUniverse: () => void;
}) {
  return (
    <div className="flex min-h-20 flex-wrap items-center gap-6 border-b border-slate-200 bg-white px-6 py-4">
      <div className="flex h-10 w-full max-w-[320px] items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-sm shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
        <input
          className="min-w-0 flex-1 bg-transparent text-slate-700 outline-none placeholder:text-slate-400"
          onChange={(event) => props.onSearchTextChange(event.target.value)}
          placeholder="搜索股票代码 / 名称（支持拼音）"
          type="search"
          value={props.searchText}
        />
        <MagnifyingGlassIcon aria-hidden="true" className="h-5 w-5 text-slate-400" />
      </div>
      <TopSelect label="证券类型" onChange={props.onInstrumentTypeChange} options={INSTRUMENT_TYPE_OPTIONS} value={props.instrumentType} />
      <TopSelect label="市场类型" onChange={props.onMarketBoardChange} options={MARKET_BOARD_OPTIONS} value={props.marketBoard} />
      <TopSelect label="上市状态" onChange={props.onListingStatusChange} options={LISTING_STATUS_OPTIONS} value={props.listingStatus} />
      <button
        className="ml-auto inline-flex h-10 items-center gap-2 rounded-md bg-blue-600 px-5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
        disabled={props.syncPending}
        onClick={props.onSyncUniverse}
        type="button"
      >
        <ArrowPathIcon aria-hidden="true" className={`h-4 w-4 ${props.syncPending ? "animate-spin" : ""}`} />
        {props.syncPending ? "刷新中" : "刷新基础标的"}
      </button>
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
  selectedSymbol: string | null;
  isPending: boolean;
  isError: boolean;
  warning: string;
  onSelect: (symbol: string) => void;
}) {
  return (
    <aside className="flex min-h-0 flex-col overflow-hidden bg-white">
      <div className="flex h-14 items-center justify-between border-b border-slate-200 px-5">
        <div className="text-sm font-semibold text-slate-950">
          全部标的
          <span className="ml-4 text-slate-500">{formatNumber(props.total)} 只</span>
        </div>
        <ChevronLeftIcon aria-hidden="true" className="h-4 w-4 text-slate-400" />
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        {props.isPending ? (
          <EmptySurface text="股票列表加载中..." />
        ) : props.isError ? (
          <EmptySurface danger text="股票列表加载失败。" />
        ) : props.instruments.length === 0 ? (
          <EmptySurface text={props.warning || "暂无匹配标的。"} />
        ) : (
          <table className="w-full table-fixed border-collapse text-left text-xs">
            <thead className="sticky top-0 z-10 bg-white text-slate-500">
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
      <div className="flex h-14 items-center gap-3 border-t border-slate-200 px-4 text-xs text-slate-500">
        <button className="inline-flex h-6 w-6 items-center justify-center rounded border border-slate-200 text-slate-300" type="button">
          <ChevronLeftIcon aria-hidden="true" className="h-3.5 w-3.5" />
        </button>
        <span className="inline-flex h-6 w-6 items-center justify-center rounded bg-blue-600 font-semibold text-white">1</span>
        <span>2</span>
        <span>3</span>
        <span>4</span>
        <span>5</span>
        <span>...</span>
        <span>{Math.max(1, Math.ceil(props.total / 100))}</span>
        <button className="inline-flex h-6 w-6 items-center justify-center rounded border border-slate-200 text-slate-500" type="button">
          <ChevronRightIcon aria-hidden="true" className="h-3.5 w-3.5" />
        </button>
        <span className="ml-auto">共 {formatNumber(props.total)} 条</span>
      </div>
    </aside>
  );
}

function InstrumentRow(props: {
  instrument: StockInstrument;
  selected: boolean;
  onSelect: (symbol: string) => void;
}) {
  const latestPrice = props.instrument.latest_price;
  const priceTone = latestPrice === undefined || latestPrice === null ? "text-slate-400" : "text-rose-500";
  return (
    <tr
      className={`cursor-pointer border-b border-slate-100 text-slate-700 hover:bg-blue-50 ${
        props.selected ? "bg-blue-50" : ""
      }`}
      onClick={() => props.onSelect(props.instrument.symbol)}
    >
      <td className="px-4 py-3 font-semibold">{props.instrument.symbol}</td>
      <td className="truncate px-3 py-3 font-semibold text-slate-800">{props.instrument.name}</td>
      <td className="px-3 py-3 text-slate-600">{props.instrument.market_board.replace("主板", "")}</td>
      <td className="px-3 py-3 text-slate-600">{props.instrument.instrument_type === "etf" ? "ETF" : "股票"}</td>
      <td className={`px-4 py-3 text-right font-semibold ${priceTone}`}>
        {latestPrice === undefined || latestPrice === null ? "--" : formatNumber(latestPrice, 3)}
      </td>
    </tr>
  );
}

function StockSummaryHeader(props: {
  instrument: StockInstrument;
  latestBar: StockDailyBar | null;
  previousBar: StockDailyBar | null;
  priceChange: number;
  priceChangeRate: number;
}) {
  const isUp = props.priceChange >= 0;
  const tone = isUp ? "text-rose-500" : "text-emerald-600";
  const labels = [
    ["今日", props.latestBar ? formatNumber(props.latestBar.open, 2) : "--", ""],
    ["最高", props.latestBar ? formatNumber(props.latestBar.high, 2) : "--", "text-rose-500"],
    ["最低", props.latestBar ? formatNumber(props.latestBar.low, 2) : "--", "text-emerald-600"],
    ["昨收", props.previousBar ? formatNumber(props.previousBar.close, 2) : "--", ""],
    ["成交量", props.latestBar ? formatCompactNumber(props.latestBar.volume) : "--", ""],
    ["成交额", props.latestBar ? `${formatNumber((props.latestBar.volume * props.latestBar.close) / 100000000, 2)}亿` : "--", ""],
    ["市盈率(TTM)", "--", ""],
    ["总市值", "--", ""],
  ];
  return (
    <header className="px-6 pb-3 pt-4">
      <div className="flex flex-wrap items-start gap-4">
        <div className="min-w-[320px]">
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-2xl font-bold text-slate-950">
              {props.instrument.symbol}
              <span className="ml-4">{props.instrument.name}</span>
            </h2>
            <span className="rounded-md bg-blue-50 px-3 py-1 text-sm font-semibold text-slate-600">{props.instrument.market_board}</span>
          </div>
          <div className="mt-1 text-xs font-medium text-slate-400">{props.instrument.name}股份有限公司</div>
          <div className="mt-5 flex flex-wrap items-end gap-4">
            <span className={`text-4xl font-bold leading-none ${tone}`}>{props.latestBar ? formatNumber(props.latestBar.close, 2) : "--"}</span>
            <span className={`pb-1 text-base font-semibold ${tone}`}>{props.latestBar ? formatSigned(props.priceChange, 2) : "--"}</span>
            <span className={`pb-1 text-base font-semibold ${tone}`}>{props.latestBar ? `${formatSigned(props.priceChangeRate, 2)}%` : "--"}</span>
          </div>
          <div className="mt-2 text-xs text-slate-500">交易中 {props.latestBar?.date ?? "--"} 10:30:00</div>
        </div>
        <div className="grid flex-1 grid-cols-2 gap-x-8 gap-y-4 pt-12 text-sm md:grid-cols-4 xl:grid-cols-8">
          {labels.map(([label, value, className]) => (
            <div key={label}>
              <div className="text-xs font-semibold text-slate-400">{label}</div>
              <div className={`mt-2 whitespace-nowrap font-semibold text-slate-700 ${className}`}>{value}</div>
            </div>
          ))}
        </div>
        <button
          className="ml-auto inline-flex h-10 items-center gap-2 rounded-md border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-600 hover:bg-slate-50"
          type="button"
        >
          <StarIcon aria-hidden="true" className="h-4 w-4" />
          加入自选
        </button>
      </div>
    </header>
  );
}

function DetailTabs() {
  return (
    <nav className="flex h-12 items-end gap-8 border-b border-slate-200 px-6 text-sm font-semibold text-slate-500">
      {DETAIL_TABS.map((tab, index) => (
        <button
          className={`relative h-12 px-1 ${index === 0 ? "text-blue-600" : "hover:text-slate-800"}`}
          key={tab}
          type="button"
        >
          {tab}
          {index === 0 ? <span className="absolute inset-x-0 bottom-0 h-0.5 rounded-full bg-blue-600" /> : null}
        </button>
      ))}
    </nav>
  );
}

function RangeToolbar(props: {
  range: MarketDataRangeSelection;
  startDate?: string;
  endDate?: string;
  refreshPending: boolean;
  onRangeChange: (range: MarketDataRangeSelection) => void;
  onRefresh: () => void;
}) {
  const [startDate, setStartDate] = useState(props.startDate ?? "2025-03-05");
  const [endDate, setEndDate] = useState(props.endDate ?? "2025-06-05");
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="inline-flex h-10 overflow-hidden rounded-md border border-slate-200 bg-white">
        {STOCK_RANGE_OPTIONS.map((option) => (
          <button
            className={`border-r border-slate-100 px-4 text-sm font-semibold last:border-r-0 ${
              props.range.type === option.value ? "bg-blue-50 text-slate-950" : "text-slate-500 hover:bg-slate-50"
            }`}
            key={option.value}
            onClick={() => props.onRangeChange({ type: option.value })}
            type="button"
          >
            {option.label}
          </button>
        ))}
      </div>
      <label className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-500">
        <input
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
      <button
        className="inline-flex h-10 items-center gap-2 rounded-md bg-blue-600 px-5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:bg-blue-300"
        disabled={props.refreshPending}
        onClick={props.onRefresh}
        type="button"
      >
        <ArrowPathIcon aria-hidden="true" className={`h-4 w-4 ${props.refreshPending ? "animate-spin" : ""}`} />
        刷新数据
      </button>
      <button className="ml-auto h-10 rounded-md border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-500" type="button">
        不复权
      </button>
    </div>
  );
}

function DailyQuoteLine(props: { bars: StockDailyBar[]; latestBar: StockDailyBar | null; previousBar: StockDailyBar | null }) {
  const latest = props.latestBar;
  const previous = props.previousBar;
  const change = latest && previous ? latest.close - previous.close : 0;
  const rate = latest && previous && previous.close !== 0 ? (change / previous.close) * 100 : 0;
  return (
    <div className="flex flex-wrap gap-4 py-3 text-xs font-semibold text-slate-500">
      <span>{latest?.date ?? "--"}</span>
      <span>开：{latest ? formatNumber(latest.open, 2) : "--"}</span>
      <span>高：<b className="text-rose-500">{latest ? formatNumber(latest.high, 2) : "--"}</b></span>
      <span>低：<b className="text-emerald-600">{latest ? formatNumber(latest.low, 2) : "--"}</b></span>
      <span>收：<b className="text-rose-500">{latest ? formatNumber(latest.close, 2) : "--"}</b></span>
      <span>涨跌：<b className={change >= 0 ? "text-rose-500" : "text-emerald-600"}>{latest ? `${formatSigned(change, 2)} (${formatSigned(rate, 2)}%)` : "--"}</b></span>
      <span>成交量：{latest ? formatCompactNumber(latest.volume) : "--"}</span>
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
    <section className="border-b border-slate-200 bg-white pb-2">
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
      tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
      legend: {
        top: 0,
        right: 16,
        itemWidth: 16,
        itemHeight: 8,
        textStyle: { color: "#64748b", fontSize: 11 },
        data: ["K线", "MA5", "MA10", "MA20", "MA60", "MA120", "成交量"],
      },
      grid: [
        { left: 54, right: 22, top: 42, height: 290 },
        { left: 54, right: 22, top: 365, height: 78 },
      ],
      xAxis: [
        { type: "category", data: labels, boundaryGap: true, axisLine: { lineStyle: { color: "#dbe3ee" } } },
        { type: "category", data: labels, gridIndex: 1, boundaryGap: true, axisLabel: { color: "#94a3b8", fontSize: 11 } },
      ],
      yAxis: [
        { type: "value", scale: true, axisLabel: { color: "#64748b" }, splitLine: { lineStyle: { color: "#edf2f7" } } },
        { type: "value", gridIndex: 1, axisLabel: { color: "#64748b" }, splitLine: { lineStyle: { color: "#edf2f7" } } },
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
    if (typeof navigator !== "undefined" && navigator.userAgent.toLowerCase().includes("jsdom")) return;
    if (!chartRef.current) return;
    const instance = echarts.init(chartRef.current, undefined, { renderer: "svg" });
    instance.setOption(option);
    return () => instance.dispose();
  }, [option]);

  return <div ref={chartRef} aria-label={`${props.symbol} 日级别行情K线`} className="h-[480px] w-full" role="img" />;
}

function FinancialCards(props: {
  isPending: boolean;
  reportType: StockFinancialReportType;
  series: StockFinancialSeries[];
  onReportTypeChange: (type: StockFinancialReportType) => void;
}) {
  const sortedSeries = FINANCIAL_ORDER.map((metric) => props.series.find((item) => item.metric === metric)).filter(
    (item): item is StockFinancialSeries => Boolean(item),
  );
  return (
    <section className="pt-4">
      <div className="mb-3 flex items-center gap-5">
        <h3 className="text-lg font-bold text-slate-950">财务数据</h3>
        <div className="flex gap-5 text-sm font-semibold">
          {(["quarterly", "yearly"] as const).map((type) => (
            <button
              className={`relative pb-2 ${props.reportType === type ? "text-blue-600" : "text-slate-500"}`}
              key={type}
              onClick={() => props.onReportTypeChange(type)}
              type="button"
            >
              {type === "quarterly" ? "季度" : "年度"}
              {props.reportType === type ? <span className="absolute inset-x-0 bottom-0 h-0.5 rounded-full bg-blue-600" /> : null}
            </button>
          ))}
        </div>
      </div>
      {props.isPending ? (
        <EmptySurface text="财报数据加载中..." />
      ) : sortedSeries.every((item) => item.points.length === 0) ? (
        <EmptySurface text="当前标的暂无可展示财报数据。" />
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 2xl:grid-cols-5">
          {sortedSeries.map((item) => (
            <FinancialMetricCard key={item.metric} series={item} />
          ))}
        </div>
      )}
    </section>
  );
}

function FinancialMetricCard(props: { series: StockFinancialSeries }) {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const latestPoint = props.series.points.at(-1);
  const previousPoint = props.series.points.at(-2);
  const changeRate =
    latestPoint && previousPoint && previousPoint.value !== 0
      ? ((latestPoint.value - previousPoint.value) / Math.abs(previousPoint.value)) * 100
      : 0;
  const option = useMemo((): echarts.EChartsOption => {
    return {
      animation: false,
      grid: { left: 28, right: 8, top: 8, bottom: 22 },
      xAxis: {
        type: "category",
        data: props.series.points.map((point) => compactPeriod(point.period)),
        axisLabel: { color: "#94a3b8", fontSize: 10 },
        axisTick: { show: false },
      },
      yAxis: { type: "value", axisLabel: { color: "#94a3b8", fontSize: 10 }, splitLine: { lineStyle: { color: "#eef2f7" } } },
      series: [
        {
          type: props.series.metric === "liability" ? "line" : "bar",
          smooth: true,
          symbol: props.series.metric === "liability" ? "circle" : "none",
          barWidth: 12,
          itemStyle: { color: "#3b82f6" },
          lineStyle: { color: "#3b82f6", width: 2 },
          data: props.series.points.map((point) => point.value),
        },
      ],
      tooltip: { trigger: "axis" },
    };
  }, [props.series]);

  useEffect(() => {
    if (typeof navigator !== "undefined" && navigator.userAgent.toLowerCase().includes("jsdom")) return;
    if (!chartRef.current) return;
    const instance = echarts.init(chartRef.current, undefined, { renderer: "svg" });
    instance.setOption(option);
    return () => instance.dispose();
  }, [option]);

  return (
    <article className="rounded-md border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="text-sm font-bold text-slate-800">{props.series.label}</h4>
          <div className="mt-1 text-xs font-semibold text-slate-500">单位：亿元</div>
        </div>
        <div className="text-right">
          <div className="text-base font-bold text-slate-950">{latestPoint ? formatNumber(latestPoint.value, 2) : "--"}</div>
          <div className={`text-xs font-bold ${changeRate >= 0 ? "text-rose-500" : "text-emerald-600"}`}>
            {latestPoint && previousPoint ? `${formatSigned(changeRate, 2)}%` : "--"}
          </div>
        </div>
      </div>
      <div ref={chartRef} aria-label={`${props.series.label} 图表`} className="mt-3 h-28 w-full" role="img" />
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
