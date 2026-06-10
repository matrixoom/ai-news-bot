import * as echarts from "echarts";
import { ArrowsPointingOutIcon } from "@heroicons/react/24/outline";
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
import { ChartFullscreen } from "../../../shared/ui/chart-fullscreen";
import { calculateSMA, MA_CONFIGS } from "../../../shared/lib/moving-average";
import { buildCartesianTheme, useWorkbenchChartTheme } from "../../../shared/charts/use-workbench-chart-theme";

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
  const [isFullscreen, setIsFullscreen] = useState(false);
  const workbenchTheme = useWorkbenchChartTheme();
  const chartTheme = useMemo(() => buildCartesianTheme(workbenchTheme), [workbenchTheme]);

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

  const maSeries = useMemo(() => {
    if (frequency !== "daily" || points.length === 0) return [];
    const result: Array<{
      name: string;
      type: "line";
      smooth: boolean;
      symbol: "none";
      lineStyle: { type: "dashed"; width: number; opacity: number };
      itemStyle: { color: string };
      data: (number | null)[];
    }> = [];
    for (const item of series) {
      const values = item.points.map((p) => p.value);
      for (const cfg of MA_CONFIGS) {
        const sma = calculateSMA(values, cfg.period);
        result.push({
          name: `${item.name} ${cfg.label}`,
          type: "line",
          smooth: true,
          symbol: "none",
          lineStyle: { type: "dashed", width: 1, opacity: 0.6 },
          itemStyle: { color: cfg.color },
          data: sma,
        });
      }
    }
    return result;
  }, [frequency, series, points.length]);

  const allSeries = useMemo(() => [...chartSeries, ...maSeries], [chartSeries, maSeries]);

  const allLegendNames = useMemo(() => {
    const names = [...legendNames];
    for (const ms of maSeries) {
      names.push(ms.name);
    }
    return names;
  }, [legendNames, maSeries]);

  const chartOption = useMemo((): echarts.EChartsOption | null => {
    if (!query.data || points.length === 0) return null;
    return {
      animation: false,
      tooltip: { trigger: "axis", ...chartTheme.tooltip },
      legend: {
        orient: "vertical",
        right: 0,
        top: "middle",
        textStyle: chartTheme.legendText,
        data: allLegendNames,
      },
      grid: { left: 48, right: 140, top: 24, bottom: 48 },
      xAxis: { type: "category", data: chartLabels, ...chartTheme.categoryAxis },
      yAxis: {
        type: "value",
        name: query.data.unit,
        ...chartTheme.valueAxis,
      },
      series: allSeries,
      dataZoom: [
        { type: "inside", zoomOnMouseWheel: true, moveOnMouseMove: true },
        { type: "slider", bottom: 8, height: 20 },
      ],
      toolbox: {
        right: 10,
        top: 4,
        feature: {
          dataZoom: { title: { zoom: "框选缩放", back: "还原" } },
          restore: { title: "重置" },
        },
      },
    };
  }, [query.data, points.length, allLegendNames, chartLabels, allSeries, chartTheme]);

  useEffect(() => {
    if (typeof navigator !== "undefined" && navigator.userAgent.toLowerCase().includes("jsdom")) {
      return;
    }
    if (!chartRef.current || !chartOption) {
      return;
    }
    const instance = echarts.init(chartRef.current, undefined, { renderer: "svg" });
    instance.setOption(chartOption);

    return () => {
      instance.dispose();
    };
  }, [chartOption]);

  return (
    <section className={`workbench-panel relative p-5${className ? ` ${className}` : ""}`}>
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-ink">{chart.title}</h3>
          <p className="mt-1 text-sm text-muted">
            单位：{chart.unit} · 频率：{chart.frequency} · 图例：{legendNames.join(" / ") || chart.title}
          </p>
        </div>
        <span className="inline-flex w-fit rounded-control border border-line bg-surface-subtle px-2.5 py-1 text-xs font-medium text-muted">
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
        <div className="mt-5 rounded-control border border-dashed border-line p-8 text-sm text-muted">图表加载中...</div>
      ) : query.isError ? (
        <div className="mt-5 rounded-control border border-negative/30 bg-negative/5 p-8 text-sm text-negative">图表数据加载失败。</div>
      ) : points.length === 0 ? (
        <div className="mt-5 rounded-control border border-dashed border-line p-8 text-sm text-muted">当前时间范围暂无数据。</div>
      ) : (
        <div className="mt-5">
          <div ref={chartRef} aria-label={`${chart.title} 图表`} role="img" className="h-72 w-full" />
          <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted">
            <span>样本数：{points.length}</span>
            <span>状态：{query.data?.sync_state.status ?? chart.status}</span>
            {query.data?.sync_state.warning_message ? <span>{query.data.sync_state.warning_message}</span> : null}
          </div>
        </div>
      )}
      <div className="absolute bottom-3 right-3 flex gap-1">
        <button
          type="button"
          className="workbench-icon-button h-8 w-8 disabled:cursor-not-allowed disabled:opacity-40"
          disabled={!chartOption}
          onClick={() => setIsFullscreen(true)}
          aria-label="全屏查看图表"
        >
          <ArrowsPointingOutIcon aria-hidden="true" className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          className="workbench-button min-h-8 px-2.5 text-xs disabled:cursor-not-allowed disabled:opacity-40"
          disabled={refreshMutation.isPending}
          onClick={() => refreshMutation.mutate()}
        >
          {refreshMutation.isPending ? "刷新中..." : refreshLabel ?? "刷新"}
        </button>
      </div>

      <ChartFullscreen
        open={isFullscreen}
        onClose={() => setIsFullscreen(false)}
        title={chart.title}
        option={chartOption}
      />
    </section>
  );
}
