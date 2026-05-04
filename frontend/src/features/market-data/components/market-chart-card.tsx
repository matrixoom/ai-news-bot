import * as echarts from "echarts";
import { useEffect, useMemo, useRef, useState } from "react";
import { useMarketDataChartQuery } from "../hooks/use-market-data-chart-query";
import { useMarketDataRefreshMutation } from "../hooks/use-market-data-refresh-mutation";
import type {
  MarketChartDefinition,
  MarketDataFrequency,
  MarketDataRangeSelection,
  MarketFrequencyOption,
  MarketRangeOption,
} from "../model/market-data.types";
import { RangeControl } from "../../../shared/ui/range-control";

type MarketChartCardProps = {
  chart: MarketChartDefinition;
  className?: string;
  frequency: MarketDataFrequency;
  frequencyOptions: MarketFrequencyOption[];
  range: MarketDataRangeSelection;
  rangeOptions: MarketRangeOption[];
  onFrequencyChange: (nextFrequency: MarketDataFrequency) => void;
  onRangeChange: (nextRange: MarketDataRangeSelection) => void;
};

export function MarketChartCard({
  chart,
  className,
  frequency,
  frequencyOptions,
  range,
  rangeOptions,
  onFrequencyChange,
  onRangeChange,
}: MarketChartCardProps) {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const query = useMarketDataChartQuery(chart.id, range, frequency);
  const refreshMutation = useMarketDataRefreshMutation(chart.id);
  const [refreshLabel, setRefreshLabel] = useState<string | null>(null);

  useEffect(() => {
    if (refreshMutation.isSuccess) {
      setRefreshLabel("已刷新");
      const timer = setTimeout(() => setRefreshLabel(null), 2000);
      return () => clearTimeout(timer);
    }
  }, [refreshMutation.isSuccess]);

  const series = query.data?.series ?? [];
  const points = series[0]?.points ?? [];
  const chartLabels = useMemo(() => points.map((point) => point.period_label || point.date), [points]);
  const legendNames = useMemo(() => series.map((item) => item.name), [series]);

  const chartSeries = useMemo(
    () =>
      series.map((item) => ({
        name: item.name,
        type: "line" as const,
        smooth: true,
        symbol: "circle",
        data: item.points.map((point) => point.value),
      })),
    [series],
  );

  useEffect(() => {
    if (typeof navigator !== "undefined" && navigator.userAgent.toLowerCase().includes("jsdom")) {
      return;
    }
    if (!chartRef.current || !query.data || points.length === 0) {
      return;
    }
    const instance = echarts.init(chartRef.current, undefined, { renderer: "svg" });
    instance.setOption({
      animation: false,
      tooltip: { trigger: "axis" },
      legend: { top: 0, data: legendNames },
      grid: { left: 48, right: 20, top: 48, bottom: 36 },
      xAxis: { type: "category", data: chartLabels },
      yAxis: {
        type: "value",
        name: query.data.unit,
      },
      series: chartSeries,
    });

    return () => {
      instance.dispose();
    };
  }, [chartLabels, chartSeries, legendNames, points.length, query.data]);

  return (
    <section className={`relative rounded-xl border border-slate-200 bg-white p-5 shadow-sm${className ? ` ${className}` : ""}`}>
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-950">{chart.title}</h3>
          <p className="mt-1 text-sm text-slate-500">
            单位：{chart.unit} · 频率：{chart.frequency} · 图例：{legendNames.join(" / ") || chart.title}
          </p>
        </div>
        <span className="inline-flex w-fit rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600">
          {rangeOptions.find((option) => option.value === range.type)?.label ?? "1年"}
        </span>
      </div>

      <div className="mt-4">
        <RangeControl
          options={rangeOptions}
          value={range}
          onChange={(nextRange) => onRangeChange(nextRange as MarketDataRangeSelection)}
          frequencyOptions={frequencyOptions}
          frequency={frequency}
          onFrequencyChange={(next) => onFrequencyChange(next as MarketDataFrequency)}
        />
      </div>

      {query.isPending ? (
        <div className="mt-5 rounded-lg border border-dashed border-slate-200 p-8 text-sm text-slate-500">图表加载中...</div>
      ) : query.isError ? (
        <div className="mt-5 rounded-lg border border-rose-200 bg-rose-50 p-8 text-sm text-rose-700">图表数据加载失败。</div>
      ) : points.length === 0 ? (
        <div className="mt-5 rounded-lg border border-dashed border-slate-200 p-8 text-sm text-slate-500">当前时间范围暂无数据。</div>
      ) : (
        <div className="mt-5">
          <div ref={chartRef} aria-label={`${chart.title} 图表`} role="img" className="h-72 w-full" />
          <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
            <span>样本数：{points.length}</span>
            <span>状态：{query.data?.sync_state.status ?? chart.status}</span>
            {query.data?.sync_state.warning_message ? <span>{query.data.sync_state.warning_message}</span> : null}
          </div>
        </div>
      )}
      <button
        type="button"
        className="absolute bottom-3 right-3 rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs font-medium text-slate-600 shadow-sm hover:bg-slate-100 disabled:cursor-not-allowed disabled:text-slate-400"
        disabled={refreshMutation.isPending}
        onClick={() => refreshMutation.mutate()}
      >
        {refreshMutation.isPending ? "刷新中..." : refreshLabel ?? "刷新"}
      </button>
    </section>
  );
}
