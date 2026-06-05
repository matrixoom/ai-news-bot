import * as echarts from "echarts";
import {
  ArrowPathIcon,
  BuildingOffice2Icon,
  ChartBarIcon,
  CircleStackIcon,
  MagnifyingGlassIcon,
} from "@heroicons/react/24/outline";
import type React from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useStockMarketDetailQuery } from "../hooks/use-stock-market-detail-query";
import { useStockMarketInstrumentsQuery } from "../hooks/use-stock-market-instruments-query";
import { useStockMarketRefreshMutation } from "../hooks/use-stock-market-refresh-mutation";
import { useStockMarketUniverseSyncMutation } from "../hooks/use-stock-market-universe-sync-mutation";
import type {
  MarketDataRangeSelection,
  StockDailyBar,
  StockFinancialReportType,
  StockInstrument,
} from "../model/market-data.types";
import { RangeControl } from "../../../shared/ui/range-control";
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

/**
 * 渲染股票市场工作区，包含标的筛选、K 线、概况和财报图。
 */
export function StockMarketWorkspace() {
  const [searchText, setSearchText] = useState("");
  const [instrumentType, setInstrumentType] = useState("all");
  const [marketBoard, setMarketBoard] = useState("all");
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [range, setRange] = useState<MarketDataRangeSelection>({ type: "3m" });
  const [financialReportType, setFinancialReportType] = useState<StockFinancialReportType>("quarterly");
  const instrumentsQuery = useStockMarketInstrumentsQuery({
    query: searchText,
    instrumentType,
    marketBoard,
  });
  const detailQuery = useStockMarketDetailQuery(selectedSymbol, range, financialReportType);
  const refreshMutation = useStockMarketRefreshMutation(selectedSymbol, range, financialReportType);
  const universeMutation = useStockMarketUniverseSyncMutation();
  const instruments = instrumentsQuery.data?.items ?? [];

  useEffect(() => {
    if (selectedSymbol || instruments.length === 0) return;
    setSelectedSymbol(instruments[0].symbol);
  }, [selectedSymbol, instruments]);

  const selectedInstrument = useMemo(
    () => instruments.find((item) => item.symbol === selectedSymbol) ?? detailQuery.data?.instrument ?? null,
    [detailQuery.data?.instrument, instruments, selectedSymbol],
  );
  const latestBar = detailQuery.data?.daily_bars.at(-1) ?? null;
  const previousBar = detailQuery.data?.daily_bars.at(-2) ?? null;
  const priceChange = latestBar && previousBar ? latestBar.close - previousBar.close : 0;
  const priceChangeRate = latestBar && previousBar && previousBar.close !== 0 ? (priceChange / previousBar.close) * 100 : 0;
  const toneClass = priceChange >= 0 ? "text-rose-500" : "text-emerald-600";

  return (
    <div className="grid min-h-[calc(100vh-9rem)] grid-cols-1 gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
      <aside className="min-h-0 overflow-hidden rounded-lg border border-slate-200 bg-white">
        <div className="border-b border-slate-200 p-4">
          <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2">
            <MagnifyingGlassIcon aria-hidden="true" className="h-4 w-4 text-slate-400" />
            <input
              className="min-w-0 flex-1 bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400"
              onChange={(event) => setSearchText(event.target.value)}
              placeholder="搜索股票代码 / 名称"
              type="search"
              value={searchText}
            />
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <SelectFilter
              label="证券类型"
              onChange={setInstrumentType}
              options={INSTRUMENT_TYPE_OPTIONS}
              value={instrumentType}
            />
            <SelectFilter
              label="市场类型"
              onChange={setMarketBoard}
              options={MARKET_BOARD_OPTIONS}
              value={marketBoard}
            />
          </div>
          <button
            className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
            disabled={universeMutation.isPending}
            onClick={() => universeMutation.mutate()}
            type="button"
          >
            <ArrowPathIcon aria-hidden="true" className={`h-4 w-4 ${universeMutation.isPending ? "animate-spin" : ""}`} />
            {universeMutation.isPending ? "刷新中" : "刷新基础标的"}
          </button>
        </div>

        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3 text-xs text-slate-500">
          <span>全部标的</span>
          <span>{instrumentsQuery.data?.total ?? 0} 只</span>
        </div>
        <div className="max-h-[calc(100vh-21rem)] overflow-y-auto">
          {instrumentsQuery.isPending ? (
            <PanelNote text="股票列表加载中..." />
          ) : instrumentsQuery.isError ? (
            <PanelNote tone="danger" text="股票列表加载失败。" />
          ) : instruments.length === 0 ? (
            <PanelNote text={instrumentsQuery.data?.warning_message || "暂无匹配标的。"} />
          ) : (
            <table className="w-full table-fixed text-left text-xs">
              <thead className="sticky top-0 z-10 bg-slate-50 text-slate-500">
                <tr>
                  <th className="w-24 px-3 py-2 font-medium">代码</th>
                  <th className="px-3 py-2 font-medium">名称</th>
                  <th className="w-20 px-3 py-2 font-medium">市场</th>
                  <th className="w-16 px-3 py-2 text-right font-medium">类型</th>
                </tr>
              </thead>
              <tbody>
                {instruments.map((item) => (
                  <StockInstrumentRow
                    instrument={item}
                    key={item.symbol}
                    onSelect={setSelectedSymbol}
                    selected={item.symbol === selectedSymbol}
                  />
                ))}
              </tbody>
            </table>
          )}
        </div>
      </aside>

      <main className="min-w-0 rounded-lg border border-slate-200 bg-white">
        {selectedInstrument ? (
          <>
            <section className="border-b border-slate-200 px-5 py-4">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-xl font-semibold text-slate-950">
                      {selectedInstrument.symbol}
                      <span className="ml-3">{selectedInstrument.name}</span>
                    </h2>
                    <span className="rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">
                      {selectedInstrument.market_board}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-wrap items-end gap-x-6 gap-y-2">
                    <span className={`text-3xl font-semibold ${toneClass}`}>
                      {latestBar ? formatNumber(latestBar.close, 2) : "--"}
                    </span>
                    <span className={`text-sm font-semibold ${toneClass}`}>
                      {latestBar ? `${formatSigned(priceChange, 2)} ${formatSigned(priceChangeRate, 2)}%` : "--"}
                    </span>
                    <span className="text-sm text-slate-500">
                      {latestBar ? `交易日 ${latestBar.date}` : "暂无日线"}
                    </span>
                  </div>
                </div>
                <button
                  className="inline-flex w-fit items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
                  disabled={!selectedSymbol || refreshMutation.isPending}
                  onClick={() => refreshMutation.mutate()}
                  type="button"
                >
                  <ArrowPathIcon aria-hidden="true" className={`h-4 w-4 ${refreshMutation.isPending ? "animate-spin" : ""}`} />
                  {refreshMutation.isPending ? "刷新中" : "刷新数据"}
                </button>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
                <MetricCell label="今日开" value={latestBar ? formatNumber(latestBar.open, 2) : "--"} />
                <MetricCell label="最高" value={latestBar ? formatNumber(latestBar.high, 2) : "--"} tone="up" />
                <MetricCell label="最低" value={latestBar ? formatNumber(latestBar.low, 2) : "--"} tone="down" />
                <MetricCell label="成交量" value={latestBar ? formatCompactNumber(latestBar.volume) : "--"} />
                <MetricCell label="MA20" value={latestBar?.ma20 ? formatNumber(latestBar.ma20, 2) : "--"} />
                <MetricCell label="样本" value={`${detailQuery.data?.sync_state.daily_point_count ?? 0} 条`} />
              </div>
            </section>

            <section className="grid gap-4 p-4 xl:grid-cols-[minmax(0,1fr)_300px]">
              <div className="min-w-0">
                <div className="mb-3">
                  <RangeControl
                    options={[...STOCK_RANGE_OPTIONS]}
                    value={range}
                    onChange={(nextRange) => setRange(nextRange as MarketDataRangeSelection)}
                  />
                </div>
                {detailQuery.isPending ? (
                  <PanelNote text="行情数据加载中..." />
                ) : detailQuery.isError ? (
                  <PanelNote tone="danger" text="行情数据加载失败。" />
                ) : detailQuery.data?.daily_bars.length === 0 ? (
                  <PanelNote text={detailQuery.data.sync_state.warning_message || "当前时间范围暂无行情数据。"} />
                ) : (
                  <StockKlineChart bars={detailQuery.data?.daily_bars ?? []} symbol={selectedInstrument.symbol} />
                )}

                <FinancialPanel
                  detailLoading={detailQuery.isPending}
                  onReportTypeChange={setFinancialReportType}
                  reportType={financialReportType}
                  series={detailQuery.data?.financials.series ?? []}
                />
              </div>

              <aside className="space-y-4">
                <InfoPanel
                  icon={<BuildingOffice2Icon aria-hidden="true" className="h-4 w-4" />}
                  title="基础信息"
                  rows={[
                    ["股票代码", selectedInstrument.symbol],
                    ["证券类型", selectedInstrument.instrument_type === "etf" ? "ETF" : "股票"],
                    ["所属板块", detailQuery.data?.profile.sector || selectedInstrument.market_board],
                    ["行业", detailQuery.data?.profile.industry || "--"],
                    ["地区", detailQuery.data?.profile.region || "--"],
                    ["上市日期", detailQuery.data?.profile.listing_date || "--"],
                  ]}
                />
                <InfoPanel
                  icon={<ChartBarIcon aria-hidden="true" className="h-4 w-4" />}
                  title="行情状态"
                  rows={[
                    ["最新交易日", detailQuery.data?.sync_state.latest_trade_date ?? "--"],
                    ["最早交易日", detailQuery.data?.sync_state.earliest_trade_date ?? "--"],
                    ["概况状态", detailQuery.data?.sync_state.profile_status ?? "--"],
                    ["财报状态", detailQuery.data?.sync_state.financial_status ?? "--"],
                    [
                      "同步时间",
                      detailQuery.data?.sync_state.synced_at ? formatLocalDateTime(detailQuery.data.sync_state.synced_at) : "--",
                    ],
                  ]}
                />
                <section className="rounded-lg border border-slate-200 p-4">
                  <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900">
                    <CircleStackIcon aria-hidden="true" className="h-4 w-4" />
                    股票属性
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {(detailQuery.data?.profile.attributes ?? []).length > 0 ? (
                      detailQuery.data?.profile.attributes.map((item) => (
                        <span className="rounded bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700" key={item}>
                          {item}
                        </span>
                      ))
                    ) : (
                      <span className="text-sm text-slate-500">--</span>
                    )}
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-600">
                    {detailQuery.data?.profile.summary || "公司概况等待上游数据补充。"}
                  </p>
                </section>
              </aside>
            </section>
          </>
        ) : (
          <PanelNote text="请选择或刷新股票标的。" />
        )}
      </main>
    </div>
  );
}

function SelectFilter(props: {
  label: string;
  options: Array<{ value: string; label: string }>;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="text-xs font-medium text-slate-500">
      {props.label}
      <select
        className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2 py-2 text-sm text-slate-800 outline-none focus:border-blue-400"
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

function StockInstrumentRow(props: {
  instrument: StockInstrument;
  selected: boolean;
  onSelect: (symbol: string) => void;
}) {
  return (
    <tr
      className={`cursor-pointer border-b border-slate-100 hover:bg-blue-50 ${props.selected ? "bg-blue-50" : ""}`}
      onClick={() => props.onSelect(props.instrument.symbol)}
    >
      <td className="px-3 py-3 font-medium text-slate-700">{props.instrument.symbol}</td>
      <td className="truncate px-3 py-3 text-slate-900">{props.instrument.name}</td>
      <td className="px-3 py-3 text-slate-500">{props.instrument.market_board}</td>
      <td className="px-3 py-3 text-right text-slate-500">
        {props.instrument.instrument_type === "etf" ? "ETF" : "股票"}
      </td>
    </tr>
  );
}

function MetricCell(props: { label: string; value: string; tone?: "up" | "down" }) {
  const toneClass = props.tone === "up" ? "text-rose-500" : props.tone === "down" ? "text-emerald-600" : "text-slate-900";
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
      <div className="text-xs text-slate-500">{props.label}</div>
      <div className={`mt-1 text-sm font-semibold ${toneClass}`}>{props.value}</div>
    </div>
  );
}

function StockKlineChart(props: { bars: StockDailyBar[]; symbol: string }) {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const option = useMemo((): echarts.EChartsOption | null => {
    if (props.bars.length === 0) return null;
    const labels = props.bars.map((bar) => bar.date);
    return {
      animation: false,
      tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
      legend: {
        top: 4,
        data: ["K线", "MA5", "MA10", "MA20", "MA60", "MA120", "成交量"],
      },
      grid: [
        { left: 54, right: 24, top: 42, height: "58%" },
        { left: 54, right: 24, top: "76%", height: "14%" },
      ],
      xAxis: [
        { type: "category", data: labels, boundaryGap: true, axisLine: { lineStyle: { color: "#cbd5e1" } } },
        { type: "category", data: labels, gridIndex: 1, boundaryGap: true, axisLabel: { show: false } },
      ],
      yAxis: [
        { type: "value", name: "价格", scale: true, splitLine: { lineStyle: { color: "#eef2f7" } } },
        { type: "value", name: "成交量", gridIndex: 1, splitLine: { show: false } },
      ],
      dataZoom: [
        { type: "inside", xAxisIndex: [0, 1] },
        { type: "slider", xAxisIndex: [0, 1], bottom: 0, height: 20 },
      ],
      series: [
        {
          name: "K线",
          type: "candlestick",
          data: props.bars.map((bar) => [bar.open, bar.close, bar.low, bar.high]),
          itemStyle: {
            color: "#ef4444",
            color0: "#10b981",
            borderColor: "#ef4444",
            borderColor0: "#10b981",
          },
        },
        ...(["ma5", "ma10", "ma20", "ma60", "ma120"] as const).map((key) => ({
          name: key.toUpperCase(),
          type: "line" as const,
          symbol: "none",
          smooth: true,
          data: props.bars.map((bar) => bar[key]),
          lineStyle: { width: 1.4 },
        })),
        {
          name: "成交量",
          type: "bar",
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: props.bars.map((bar) => bar.volume),
          itemStyle: { color: "#93c5fd" },
        },
      ],
    };
  }, [props.bars]);

  useEffect(() => {
    if (typeof navigator !== "undefined" && navigator.userAgent.toLowerCase().includes("jsdom")) return;
    if (!chartRef.current || !option) return;
    const instance = echarts.init(chartRef.current, undefined, { renderer: "svg" });
    instance.setOption(option);
    return () => instance.dispose();
  }, [option]);

  return (
    <section className="rounded-lg border border-slate-200 p-4">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-base font-semibold text-slate-950">{props.symbol} 日级别行情K线</h3>
        <span className="text-xs text-slate-500">开盘 / 收盘 / 最高 / 最低 / 成交量</span>
      </div>
      <div ref={chartRef} aria-label={`${props.symbol} K线图`} className="h-[420px] w-full" role="img" />
    </section>
  );
}

function FinancialPanel(props: {
  detailLoading: boolean;
  reportType: StockFinancialReportType;
  series: Array<{ metric: string; label: string; points: Array<{ period: string; value: number; unit: string }> }>;
  onReportTypeChange: (value: StockFinancialReportType) => void;
}) {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const option = useMemo((): echarts.EChartsOption | null => {
    const labels = Array.from(new Set(props.series.flatMap((item) => item.points.map((point) => point.period)))).sort();
    if (labels.length === 0) return null;
    return {
      animation: false,
      tooltip: { trigger: "axis" },
      legend: { top: 0, data: props.series.map((item) => item.label) },
      grid: { left: 54, right: 20, top: 42, bottom: 42 },
      xAxis: { type: "category", data: labels },
      yAxis: { type: "value", name: "亿元" },
      series: props.series.map((item) => {
        const pointByPeriod = new Map(item.points.map((point) => [point.period, point.value]));
        return {
          name: item.label,
          type: "bar" as const,
          data: labels.map((label) => pointByPeriod.get(label) ?? null),
          barMaxWidth: 26,
        };
      }),
    };
  }, [props.series]);

  useEffect(() => {
    if (typeof navigator !== "undefined" && navigator.userAgent.toLowerCase().includes("jsdom")) return;
    if (!chartRef.current || !option) return;
    const instance = echarts.init(chartRef.current, undefined, { renderer: "svg" });
    instance.setOption(option);
    return () => instance.dispose();
  }, [option]);

  return (
    <section className="mt-4 rounded-lg border border-slate-200 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-base font-semibold text-slate-950">财务数据</h3>
        <div className="inline-flex overflow-hidden rounded-lg border border-slate-200">
          {(["quarterly", "yearly"] as const).map((item) => (
            <button
              className={`px-3 py-1.5 text-sm font-medium ${
                props.reportType === item ? "bg-blue-600 text-white" : "bg-white text-slate-600 hover:bg-slate-50"
              }`}
              key={item}
              onClick={() => props.onReportTypeChange(item)}
              type="button"
            >
              {item === "quarterly" ? "季度" : "年度"}
            </button>
          ))}
        </div>
      </div>
      {props.detailLoading ? (
        <PanelNote text="财报数据加载中..." />
      ) : option ? (
        <div ref={chartRef} aria-label="财务数据图表" className="h-72 w-full" role="img" />
      ) : (
        <PanelNote text="当前标的暂无可展示财报数据。" />
      )}
    </section>
  );
}

function InfoPanel(props: { title: string; icon: React.ReactNode; rows: Array<[string, string]> }) {
  return (
    <section className="rounded-lg border border-slate-200 p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900">
        {props.icon}
        {props.title}
      </div>
      <dl className="space-y-2 text-sm">
        {props.rows.map(([label, value]) => (
          <div className="flex items-start justify-between gap-4" key={label}>
            <dt className="text-slate-500">{label}</dt>
            <dd className="text-right font-medium text-slate-800">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function PanelNote(props: { text: string; tone?: "default" | "danger" }) {
  const className =
    props.tone === "danger"
      ? "border-rose-200 bg-rose-50 text-rose-700"
      : "border-dashed border-slate-200 bg-white text-slate-500";
  return <div className={`m-4 rounded-lg border p-8 text-sm ${className}`}>{props.text}</div>;
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
