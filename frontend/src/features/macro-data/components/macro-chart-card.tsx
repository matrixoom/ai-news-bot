import * as echarts from "echarts";
import { ArrowsPointingOutIcon } from "@heroicons/react/24/outline";
import { useEffect, useMemo, useRef, useState } from "react";
import { useMacroDataChartQuery } from "../hooks/use-macro-data-chart-query";
import { useMacroDataRefreshMutation } from "../hooks/use-macro-data-refresh-mutation";
import type {
  MacroChartDefinition,
  MacroDataFrequency,
  MacroDataRangeSelection,
  MacroFrequencyOption,
  MacroRangeOption,
} from "../model/macro-data.types";
import { RangeControl } from "../../../shared/ui/range-control";
import { ChartFullscreen } from "../../../shared/ui/chart-fullscreen";

type MacroChartCardProps = {
  chart: MacroChartDefinition;
  className?: string;
  frequency: MacroDataFrequency;
  frequencyOptions: MacroFrequencyOption[];
  range: MacroDataRangeSelection;
  rangeOptions: MacroRangeOption[];
  onFrequencyChange: (nextFrequency: MacroDataFrequency) => void;
  onRangeChange: (nextRange: MacroDataRangeSelection) => void;
};

const STACKED_LINE_COLORS = ["#4f46e5", "#a3c72a", "#334155", "#fb923c", "#0ea5e9"];

type AxisTooltipParam = {
  axisValue?: unknown;
  axisValueLabel?: unknown;
  marker?: unknown;
  seriesName?: string;
  value?: unknown;
};

/**
 * 转义 tooltip 中的文本字段，避免序列名或标签被当作 HTML 片段渲染。
 *
 * Args:
 *   value: 需要展示到 tooltip 的原始文本。
 *
 * Returns:
 *   可安全拼接进 HTML tooltip 的文本。
 */
function escapeTooltipText(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * 格式化 tooltip 中的数值，保持财经图表常见的千分位与最多两位小数。
 *
 * Args:
 *   value: ECharts 传入的原始数据值，可能是数字、空值或数组结构。
 *
 * Returns:
 *   面向用户展示的数值文本。
 */
function formatTooltipValue(value: unknown): string {
  if (Array.isArray(value)) {
    return formatTooltipValue(value.at(-1));
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(value);
  }
  if (typeof value === "string" && value.trim()) {
    return escapeTooltipText(value);
  }
  return "-";
}

/**
 * 归一化 ECharts tooltip 参数，兼容单点、数组以及 marker 非字符串的情况。
 *
 * Args:
 *   params: ECharts formatter 回调传入的原始参数。
 *
 * Returns:
 *   可供 tooltip 去重与渲染使用的参数列表。
 */
function normalizeAxisTooltipParams(params: unknown): AxisTooltipParam[] {
  const rawItems = Array.isArray(params) ? params : [params];
  return rawItems.flatMap((item) => {
    if (!item || typeof item !== "object") {
      return [];
    }
    const record = item as Record<string, unknown>;
    return [
      {
        axisValue: record.axisValue,
        axisValueLabel: record.axisValueLabel,
        marker: record.marker,
        seriesName: typeof record.seriesName === "string" ? record.seriesName : undefined,
        value: record.value,
      },
    ];
  });
}

/**
 * 为柱线绑定的组合图表生成 axis tooltip，按业务序列名去重。
 *
 * Args:
 *   params: ECharts 在 axis trigger 下传入的 tooltip 参数列表。
 *
 * Returns:
 *   去除同名柱/线重复项后的 HTML tooltip。
 */
function formatDeduplicatedAxisTooltip(params: unknown): string {
  const items = normalizeAxisTooltipParams(params);
  const firstItem = items[0];
  const title = firstItem?.axisValueLabel ?? firstItem?.axisValue ?? "";
  const seenNames = new Set<string>();
  const rows: string[] = [];

  for (const item of items) {
    const seriesName = item.seriesName;
    if (!seriesName || seenNames.has(seriesName)) {
      continue;
    }
    seenNames.add(seriesName);
    const marker = typeof item.marker === "string" ? item.marker : "";
    rows.push(
      `<div>${marker}<span>${escapeTooltipText(seriesName)}</span><span style="float:right;margin-left:16px;font-weight:600;">${formatTooltipValue(item.value)}</span></div>`,
    );
  }

  return [`<div>${escapeTooltipText(String(title))}</div>`, ...rows].join("");
}

export function MacroChartCard({
  chart,
  className,
  frequency,
  frequencyOptions,
  range,
  rangeOptions,
  onFrequencyChange,
  onRangeChange,
}: MacroChartCardProps) {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const query = useMacroDataChartQuery(chart.id, range, frequency);
  const refreshMutation = useMacroDataRefreshMutation(chart.id);
  const [refreshLabel, setRefreshLabel] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    if (refreshMutation.isSuccess) {
      setRefreshLabel("已刷新");
      const timer = setTimeout(() => setRefreshLabel(null), 2000);
      return () => clearTimeout(timer);
    }
  }, [refreshMutation.isSuccess]);

  const series = query.data?.series ?? [];
  const chartPointIndex = useMemo(() => {
    const pointsByDate = new Map<string, string>();
    for (const item of series) {
      for (const point of item.points) {
        pointsByDate.set(point.date, point.period_label || point.date);
      }
    }
    return Array.from(pointsByDate.entries()).sort(([leftDate], [rightDate]) => leftDate.localeCompare(rightDate));
  }, [series]);
  const chartDates = useMemo(() => chartPointIndex.map(([date]) => date), [chartPointIndex]);
  const chartLabels = useMemo(() => chartPointIndex.map(([, label]) => label), [chartPointIndex]);
  const legendNames = useMemo(() => series.map((item) => item.name), [series]);
  const chartType = query.data?.chart_type ?? "line";
  const isWide = query.data?.wide === true || chartType === "bar_stacked" || chartType === "bar_stacked_line";
  const isPMI = chart.id.includes("pmi");

  const pmiYRange = useMemo(() => {
    if (!isPMI) return null;
    const allValues = series.flatMap((s) => s.points.map((p) => p.value));
    if (allValues.length === 0) return null;
    const dataMin = Math.min(...allValues);
    const dataMax = Math.max(...allValues);
    const maxDist = Math.max(Math.abs(dataMax - 50), Math.abs(dataMin - 50), 1.5);
    const rawHalf = maxDist / 0.70;
    const halfRange = Math.ceil(rawHalf);
    return { min: 50 - halfRange, max: 50 + halfRange };
  }, [isPMI, series]);

  const chartSeries = useMemo<echarts.SeriesOption[]>(
    () =>
      series.flatMap<echarts.SeriesOption>((item, index) => {
        const valueByDate = new Map(item.points.map((point) => [point.date, point.value]));
        const data = chartDates.map((date) => valueByDate.get(date) ?? null);
        const color = STACKED_LINE_COLORS[index % STACKED_LINE_COLORS.length];
        if (chartType === "bar_stacked") {
          return {
            name: item.name,
            type: "bar" as const,
            stack: "total",
            data,
            itemStyle: { color },
          } as echarts.SeriesOption;
        }
        const lineSeries: Record<string, unknown> = {
          name: item.name,
          type: "line" as const,
          smooth: chartType !== "bar_stacked_line",
          symbol: "circle",
          data,
        };
        if (chartType === "bar_stacked_line") {
          if (index > 0) {
            return [
              {
                name: item.name,
                type: "bar" as const,
                stack: "total",
                data,
                itemStyle: { color },
              },
              {
                name: item.name,
                type: "line" as const,
                smooth: false,
                symbol: "circle",
                data,
                itemStyle: { color },
                lineStyle: { color, type: "dashed", width: 1.6, opacity: 0.85 },
                z: 4,
              },
            ] as echarts.SeriesOption[];
          }
          lineSeries.itemStyle = { color };
          lineSeries.lineStyle = { color, type: "dashed", width: 2 };
          lineSeries.z = 3;
        }
        if (isPMI && index === 0) {
          lineSeries.markLine = {
            silent: true,
            symbol: "none",
            lineStyle: { color: "#fca5a5", type: "dashed", width: 1.5 },
            label: {
              show: true,
              position: "end",
              formatter: "",
              fontSize: 11,
              color: "#ef4444",
            },
            data: [{ yAxis: 50 }],
          };
        }
        return lineSeries as echarts.SeriesOption;
      }),
    [chartType, series, chartDates, isPMI],
  );

  const chartOption = useMemo((): echarts.EChartsOption | null => {
    if (!query.data || chartDates.length === 0) return null;
    const zoom: echarts.EChartsOption = {
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
    const tooltip: echarts.EChartsOption["tooltip"] =
      chartType === "bar_stacked_line"
        ? { trigger: "axis", formatter: (params: unknown) => formatDeduplicatedAxisTooltip(params) }
        : { trigger: "axis" };

    if (isWide) {
      return {
        animation: false,
        tooltip,
        legend: {
          orient: "vertical",
          right: 0,
          top: "middle",
          textStyle: { fontSize: 11 },
          data: legendNames,
        },
        grid: { left: 48, right: 140, top: 24, bottom: 48 },
        xAxis: { type: "category", data: chartLabels },
        yAxis: {
          type: "value",
          name: query.data.unit,
          ...(pmiYRange ? { min: pmiYRange.min, max: pmiYRange.max } : {}),
        },
        series: chartSeries,
        ...zoom,
      };
    }
    return {
      animation: false,
      tooltip,
      legend: { top: 0, data: legendNames },
      grid: { left: 48, right: 20, top: 48, bottom: 48 },
      xAxis: { type: "category", data: chartLabels },
      yAxis: {
        type: "value",
        name: query.data.unit,
        ...(pmiYRange ? { min: pmiYRange.min, max: pmiYRange.max } : {}),
      },
      series: chartSeries,
      ...zoom,
    };
  }, [query.data, chartDates.length, chartType, isWide, legendNames, chartLabels, chartSeries, pmiYRange]);

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
    <section className={`relative rounded-xl border border-slate-200 bg-white p-5 shadow-sm${className ? ` ${className}` : ""}`}>
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-950">{chart.title}</h3>
          <p className="mt-1 text-sm text-slate-500">
            单位：{chart.unit} · 频率：{chart.frequency}{isWide ? "" : ` · 图例：${legendNames.join(" / ") || chart.title}`}
          </p>
        </div>
        <span className="inline-flex w-fit rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600">
          {rangeOptions.find((option) => option.value === range.type)?.label ?? "一年"}
        </span>
      </div>

      <div className="mt-4">
        <RangeControl
          options={rangeOptions}
          value={range}
          onChange={(nextRange) => onRangeChange(nextRange as MacroDataRangeSelection)}
          frequencyOptions={frequencyOptions}
          frequency={frequency}
          onFrequencyChange={(next) => onFrequencyChange(next as MacroDataFrequency)}
        />
      </div>

      {query.isPending ? (
        <div className="mt-5 rounded-lg border border-dashed border-slate-200 p-8 text-sm text-slate-500">图表加载中...</div>
      ) : query.isError ? (
        <div className="mt-5 rounded-lg border border-rose-200 bg-rose-50 p-8 text-sm text-rose-700">图表数据加载失败。</div>
      ) : chartDates.length === 0 ? (
        <div className="mt-5 rounded-lg border border-dashed border-slate-200 p-8 text-sm text-slate-500">当前时间范围暂无数据。</div>
      ) : (
        <div className="mt-5">
          <div ref={chartRef} aria-label={`${chart.title} 图表`} role="img" className="h-72 w-full" />
          <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
            <span>样本数：{chartDates.length}</span>
            <span>状态：{query.data?.sync_state.status ?? chart.status}</span>
            {query.data?.sync_state.warning_message ? <span>{query.data.sync_state.warning_message}</span> : null}
          </div>
        </div>
      )}
      <div className="absolute bottom-3 right-3 flex gap-1">
        <button
          type="button"
          className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs font-medium text-slate-600 shadow-sm hover:bg-slate-100 disabled:cursor-not-allowed disabled:text-slate-400"
          disabled={!chartOption}
          onClick={() => setIsFullscreen(true)}
          aria-label="全屏查看图表"
        >
          <ArrowsPointingOutIcon aria-hidden="true" className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs font-medium text-slate-600 shadow-sm hover:bg-slate-100 disabled:cursor-not-allowed disabled:text-slate-400"
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
