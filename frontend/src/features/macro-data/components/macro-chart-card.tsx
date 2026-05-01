import * as echarts from "echarts";
import { useEffect, useMemo, useRef } from "react";
import { useMacroDataChartQuery } from "../hooks/use-macro-data-chart-query";
import type { MacroChartDefinition, MacroDataRangeSelection, MacroRangeOption } from "../model/macro-data.types";
import { MacroRangeControl } from "./macro-range-control";

type MacroChartCardProps = {
  chart: MacroChartDefinition;
  range: MacroDataRangeSelection;
  rangeOptions: MacroRangeOption[];
  onRangeChange: (nextRange: MacroDataRangeSelection) => void;
};

export function MacroChartCard({ chart, range, rangeOptions, onRangeChange }: MacroChartCardProps) {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const query = useMacroDataChartQuery(chart.id, range);
  const points = query.data?.series[0]?.points ?? [];
  const chartLabels = useMemo(() => points.map((point) => point.period_label || point.date), [points]);
  const chartValues = useMemo(() => points.map((point) => point.value), [points]);

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
      legend: { top: 0, data: [query.data.series[0]?.name ?? chart.title] },
      grid: { left: 48, right: 20, top: 48, bottom: 36 },
      xAxis: { type: "category", data: chartLabels },
      yAxis: { type: "value", name: query.data.unit },
      series: [
        {
          name: query.data.series[0]?.name ?? chart.title,
          type: "line",
          smooth: true,
          symbol: "circle",
          data: chartValues,
        },
      ],
    });

    return () => {
      instance.dispose();
    };
  }, [chart.title, chartLabels, chartValues, points.length, query.data]);

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-950">{chart.title}</h3>
          <p className="mt-1 text-sm text-slate-500">
            单位：{chart.unit} · 频率：{chart.frequency} · 图例：{chart.title}
          </p>
        </div>
        <span className="inline-flex w-fit rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600">
          {rangeOptions.find((option) => option.value === range.type)?.label ?? "一年"}
        </span>
      </div>

      <div className="mt-4">
        <MacroRangeControl options={rangeOptions} value={range} onChange={onRangeChange} />
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
    </section>
  );
}
