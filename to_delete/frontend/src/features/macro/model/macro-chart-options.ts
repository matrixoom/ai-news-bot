import type { EChartsOption } from "echarts";
import type { MacroComparisonSection, MacroIndicatorPoint, MacroIndicatorView, MacroModuleViewModel } from "./macro-module.types";

type PairTimelineRow = {
  periodEnd: string;
  periodLabel: string;
  primary: number | null;
  secondary: number | null;
  delta: number | null;
};

/**
 * 合并主指标、次指标与差值序列，保证组合图共用同一条时间轴。
 * @param section 宏观对比区块。
 * @returns 按时间升序排列的统一时间轴数据。
 */
function buildPairTimeline(section: MacroComparisonSection): PairTimelineRow[] {
  const rows = new Map<string, PairTimelineRow>();

  const upsertRow = (point: MacroIndicatorPoint) => {
    const existing = rows.get(point.periodEnd);

    if (existing) {
      if (!existing.periodLabel) {
        existing.periodLabel = point.periodLabel;
      }
      return existing;
    }

    const nextRow: PairTimelineRow = {
      periodEnd: point.periodEnd,
      periodLabel: point.periodLabel,
      primary: null,
      secondary: null,
      delta: null,
    };
    rows.set(point.periodEnd, nextRow);
    return nextRow;
  };

  for (const point of section.primary.points) {
    upsertRow(point).primary = point.value;
  }

  for (const point of section.secondary?.points ?? []) {
    upsertRow(point).secondary = point.value;
  }

  for (const point of section.deltaPoints) {
    upsertRow(point).delta = point.value;
  }

  return Array.from(rows.values()).sort((left, right) => left.periodEnd.localeCompare(right.periodEnd));
}

/**
 * 根据单位格式化数值，避免图表轴标签过长。
 * @param value 数值。
 * @param unit 指标单位。
 * @returns 适合图表展示的短格式文本。
 */
function formatUnitValue(value: number, unit: string): string {
  const digits = Math.abs(value) >= 100 ? 0 : Math.abs(value) >= 10 ? 1 : 2;
  const normalized = value.toFixed(digits).replace(/\.0+$/, "").replace(/(\.\d*?)0+$/, "$1");
  return unit ? `${normalized}${unit}` : normalized;
}

/**
 * 解析字符串数值，供总览统计和摘要使用。
 * @param value 原始字符串数值。
 * @returns 可解析时返回数值，否则返回 null。
 */
function parseNumericValue(value: string): number | null {
  const normalized = Number(value.replace(/,/g, "").replace(/[^\d.+-]/g, ""));
  return Number.isFinite(normalized) ? normalized : null;
}

/**
 * 构建对比页组合图配置，主次指标走双轴，差值走底部柱状区。
 * @param section 宏观对比区块。
 * @returns ECharts 图表配置。
 */
export function buildComparisonChartOption(section: MacroComparisonSection): EChartsOption {
  const timeline = buildPairTimeline(section);
  const hasSecondary = section.secondary !== null;
  const hasDelta = timeline.some((item) => item.delta !== null);
  const labels = timeline.map((item) => item.periodLabel);
  const series = [
    {
      name: section.primary.label,
      type: "line" as const,
      smooth: true,
      symbol: "circle",
      symbolSize: 7,
      data: timeline.map((item) => item.primary),
      lineStyle: { width: 3 },
      itemStyle: { color: "#0f172a" },
      areaStyle: { color: "rgba(15, 23, 42, 0.08)" },
      emphasis: { focus: "series" as const },
    },
    ...(hasSecondary
      ? [
          {
            name: section.secondary!.label,
            type: "line" as const,
            smooth: true,
            symbol: "circle",
            symbolSize: 7,
            yAxisIndex: 1,
            data: timeline.map((item) => item.secondary),
            lineStyle: { width: 3 },
            itemStyle: { color: "#2563eb" },
            areaStyle: { color: "rgba(37, 99, 235, 0.08)" },
            emphasis: { focus: "series" as const },
          },
        ]
      : []),
    ...(hasDelta
      ? [
          {
            name: section.deltaLabel,
            type: "bar" as const,
            xAxisIndex: 1,
            yAxisIndex: 2,
            data: timeline.map((item) => item.delta),
            barMaxWidth: 24,
            itemStyle: {
              color: "#d97706",
              borderRadius: [8, 8, 0, 0],
            },
            markLine: {
              silent: true,
              symbol: "none",
              lineStyle: { color: "#94a3b8", type: "dashed" as const },
              data: [{ yAxis: 0 }],
            },
          },
        ]
      : []),
  ] as EChartsOption["series"];

  return {
    animation: false,
    color: ["#0f172a", "#2563eb", "#d97706"],
    grid: hasDelta
      ? [
          { left: 56, right: 56, top: 52, height: "46%" },
          { left: 56, right: 56, top: "72%", height: "16%" },
        ]
      : [{ left: 56, right: 56, top: 52, bottom: 40 }],
    legend: {
      top: 8,
      right: 16,
      itemWidth: 14,
      itemHeight: 8,
      textStyle: {
        color: "#475569",
        fontSize: 12,
      },
      data: [section.primary.label, ...(hasSecondary ? [section.secondary!.label] : []), ...(hasDelta ? [section.deltaLabel] : [])],
    },
    tooltip: {
      trigger: "axis",
      axisPointer: {
        type: "cross",
      },
    },
    xAxis: hasDelta
      ? [
          {
            type: "category",
            boundaryGap: false,
            data: labels,
            axisLabel: { color: "#64748b", fontSize: 11 },
            axisLine: { lineStyle: { color: "#cbd5e1" } },
          },
          {
            type: "category",
            gridIndex: 1,
            data: labels,
            axisLabel: { color: "#64748b", fontSize: 11 },
            axisLine: { lineStyle: { color: "#cbd5e1" } },
          },
        ]
      : [
          {
            type: "category",
            boundaryGap: false,
            data: labels,
            axisLabel: { color: "#64748b", fontSize: 11 },
            axisLine: { lineStyle: { color: "#cbd5e1" } },
          },
        ],
    yAxis: hasDelta
      ? [
          {
            type: "value",
            axisLabel: {
              color: "#64748b",
              formatter: (value: number) => formatUnitValue(value, section.primary.unit),
            },
            splitLine: { lineStyle: { color: "#e2e8f0" } },
          },
          {
            type: "value",
            position: "right",
            axisLabel: {
              color: "#64748b",
              formatter: (value: number) => formatUnitValue(value, section.secondary?.unit ?? section.primary.unit),
            },
            splitLine: { show: false },
          },
          {
            type: "value",
            gridIndex: 1,
            axisLabel: {
              color: "#64748b",
              formatter: (value: number) => formatUnitValue(value, section.primary.unit),
            },
            splitLine: { show: false },
          },
        ]
      : [
          {
            type: "value",
            axisLabel: {
              color: "#64748b",
              formatter: (value: number) => formatUnitValue(value, section.primary.unit),
            },
            splitLine: { lineStyle: { color: "#e2e8f0" } },
          },
          {
            type: "value",
            position: "right",
            axisLabel: {
              color: "#64748b",
              formatter: (value: number) => formatUnitValue(value, section.secondary?.unit ?? section.primary.unit),
            },
            splitLine: { show: false },
          },
        ],
    series,
  };
}

/**
 * 构建单指标时间序列图，突出趋势斜率与均值位置。
 * @param indicator 指标视图。
 * @returns ECharts 图表配置。
 */
export function buildIndicatorChartOption(indicator: MacroIndicatorView): EChartsOption {
  return {
    animation: false,
    color: ["#0f172a"],
    grid: { left: 48, right: 24, top: 24, bottom: 36 },
    tooltip: {
      trigger: "axis",
      axisPointer: {
        type: "line",
      },
    },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: indicator.points.map((point) => point.periodLabel),
      axisLabel: { color: "#64748b", fontSize: 11 },
      axisLine: { lineStyle: { color: "#cbd5e1" } },
    },
    yAxis: {
      type: "value",
      axisLabel: {
        color: "#64748b",
        formatter: (value: number) => formatUnitValue(value, indicator.unit),
      },
      splitLine: { lineStyle: { color: "#e2e8f0" } },
    },
    series: [
      {
        name: indicator.label,
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 7,
        data: indicator.points.map((point) => point.value),
        lineStyle: { width: 3 },
        areaStyle: { color: "rgba(15, 23, 42, 0.08)" },
        markLine: {
          symbol: "none",
          lineStyle: { color: "#94a3b8", type: "dashed" },
          label: { color: "#64748b" },
          data: [{ type: "average", name: "Average" }],
        },
      },
    ],
  };
}

/**
 * 构建总览差值监控图，用于快速识别各对比组的最新偏离方向。
 * @param model 宏观模块视图模型。
 * @returns ECharts 图表配置。
 */
export function buildGapMonitorOption(model: MacroModuleViewModel): EChartsOption {
  const rows = model.comparisonSections.map((section) => {
    const latestPoint = section.deltaPoints[section.deltaPoints.length - 1];
    return {
      label: section.title,
      value: latestPoint?.value ?? 0,
    };
  });

  return {
    animation: false,
    grid: { left: 120, right: 24, top: 24, bottom: 24 },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: {
      type: "value",
      axisLabel: { color: "#64748b" },
      splitLine: { lineStyle: { color: "#e2e8f0" } },
    },
    yAxis: {
      type: "category",
      data: rows.map((row) => row.label),
      axisLabel: { color: "#475569", fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        type: "bar",
        data: rows.map((row) => row.value),
        barMaxWidth: 22,
        itemStyle: {
          color: (params: { value?: unknown }) => {
            const value = typeof params.value === "number" ? params.value : Number(params.value ?? 0);
            return value >= 0 ? "#0f766e" : "#b45309";
          },
          borderRadius: [0, 8, 8, 0],
        },
      },
    ] as EChartsOption["series"],
  };
}

/**
 * 构建覆盖度图，帮助确认哪些指标具备可用于分析的历史深度。
 * @param model 宏观模块视图模型。
 * @returns ECharts 图表配置。
 */
export function buildHistoryCoverageOption(model: MacroModuleViewModel): EChartsOption {
  const rows = model.indicators.map((indicator) => ({
    label: indicator.label,
    value: indicator.points.length,
  }));

  return {
    animation: false,
    grid: { left: 96, right: 24, top: 24, bottom: 24 },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: {
      type: "value",
      axisLabel: { color: "#64748b" },
      splitLine: { lineStyle: { color: "#e2e8f0" } },
    },
    yAxis: {
      type: "category",
      data: rows.map((row) => row.label),
      axisLabel: { color: "#475569", fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        type: "bar",
        data: rows.map((row) => row.value),
        barMaxWidth: 22,
        itemStyle: {
          color: "#1d4ed8",
          borderRadius: [0, 8, 8, 0],
        },
      },
    ] as EChartsOption["series"],
  };
}

/**
 * 统计带历史序列的指标数量。
 * @param model 宏观模块视图模型。
 * @returns 具备历史点位的指标数量。
 */
export function countIndicatorsWithHistory(model: MacroModuleViewModel): number {
  return model.indicators.filter((indicator) => indicator.points.length > 0).length;
}

/**
 * 汇总全部指标的历史点数量。
 * @param model 宏观模块视图模型。
 * @returns 历史点总数。
 */
export function countHistoryPoints(model: MacroModuleViewModel): number {
  return model.indicators.reduce((total, indicator) => total + indicator.points.length, 0);
}

/**
 * 解析模块中最新的周期标签，方便总览展示最新更新覆盖范围。
 * @param model 宏观模块视图模型。
 * @returns 最新周期标签文本。
 */
export function resolveFreshestPeriodLabel(model: MacroModuleViewModel): string {
  for (const indicator of model.indicators) {
    if (indicator.periodLabel) {
      return indicator.periodLabel;
    }
  }

  return "No recent period";
}

/**
 * 生成指标历史区间文本。
 * @param indicator 指标视图。
 * @returns 历史区间文本。
 */
export function resolveIndicatorRange(indicator: MacroIndicatorView): string {
  if (!indicator.points.length) {
    return "No historical range";
  }

  const values = indicator.points.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  return `${formatUnitValue(min, indicator.unit)} - ${formatUnitValue(max, indicator.unit)}`;
}

/**
 * 生成指标历史均值文本。
 * @param indicator 指标视图。
 * @returns 历史均值文本。
 */
export function resolveIndicatorAverage(indicator: MacroIndicatorView): string {
  if (!indicator.points.length) {
    return "No average yet";
  }

  const sum = indicator.points.reduce((total, point) => total + point.value, 0);
  return formatUnitValue(sum / indicator.points.length, indicator.unit);
}

/**
 * 生成指标最近一次数值变化文本。
 * @param indicator 指标视图。
 * @returns 最近变化文本。
 */
export function resolveIndicatorDelta(indicator: MacroIndicatorView): string {
  if (indicator.points.length < 2) {
    return indicator.changeLabel || "No prior observation";
  }

  const latest = indicator.points[indicator.points.length - 1]!.value;
  const previous = indicator.points[indicator.points.length - 2]!.value;
  const delta = latest - previous;
  const sign = delta > 0 ? "+" : "";
  return `${sign}${formatUnitValue(delta, indicator.unit)}`;
}

/**
 * 解析最近值，供总览卡片显示。
 * @param indicator 指标视图。
 * @returns 数值或 null。
 */
export function resolveIndicatorLatestNumericValue(indicator: MacroIndicatorView): number | null {
  const latestPoint = indicator.points[indicator.points.length - 1];
  if (latestPoint) {
    return latestPoint.value;
  }

  return parseNumericValue(indicator.latestValue);
}
