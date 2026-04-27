import type { EChartsOption } from "echarts";
import type { MacroComparisonSection, MacroIndicatorView } from "./macro-module.types";

type PairAlignedPoint = {
  periodEnd: string;
  periodLabel: string;
  primary: number | null;
  secondary: number | null;
};

type PairStat = {
  label: string;
  value: string;
};

/**
 * 将两条指标序列对齐到同一时间轴，便于做相对走势和统计分析。
 * @param section 宏观配对区块。
 * @returns 按时间升序排列的对齐点位。
 */
function buildAlignedPairTimeline(section: MacroComparisonSection): PairAlignedPoint[] {
  const rows = new Map<string, PairAlignedPoint>();

  const ensureRow = (periodEnd: string, periodLabel: string) => {
    const existing = rows.get(periodEnd);
    if (existing) {
      if (!existing.periodLabel) {
        existing.periodLabel = periodLabel;
      }
      return existing;
    }

    const nextRow: PairAlignedPoint = {
      periodEnd,
      periodLabel,
      primary: null,
      secondary: null,
    };
    rows.set(periodEnd, nextRow);
    return nextRow;
  };

  for (const point of section.primary.points) {
    ensureRow(point.periodEnd, point.periodLabel).primary = point.value;
  }

  for (const point of section.secondary?.points ?? []) {
    ensureRow(point.periodEnd, point.periodLabel).secondary = point.value;
  }

  return Array.from(rows.values()).sort((left, right) => left.periodEnd.localeCompare(right.periodEnd));
}

/**
 * 过滤出主次指标同时存在的重叠区间，用于配对分析。
 * @param section 宏观配对区块。
 * @returns 可用于统计分析的重叠序列。
 */
function buildOverlappingTimeline(section: MacroComparisonSection): PairAlignedPoint[] {
  return buildAlignedPairTimeline(section).filter((point) => point.primary !== null && point.secondary !== null);
}

/**
 * 将序列基准化到 100，便于跨量纲比较相对强弱。
 * @param values 原始数值序列。
 * @returns 基准化后的序列。
 */
function rebaseTo100(values: number[]): number[] {
  if (!values.length || values[0] === 0) {
    return values.map(() => 100);
  }

  const base = values[0]!;
  return values.map((value) => Number(((value / base) * 100).toFixed(2)));
}

/**
 * 格式化图表和统计用的数值文本。
 * @param value 数值。
 * @param unit 指标单位。
 * @returns 紧凑数值文本。
 */
function formatUnitValue(value: number, unit: string): string {
  const digits = Math.abs(value) >= 100 ? 0 : Math.abs(value) >= 10 ? 1 : 2;
  const normalized = value.toFixed(digits).replace(/\.0+$/, "").replace(/(\.\d*?)0+$/, "$1");
  return unit ? `${normalized}${unit}` : normalized;
}

/**
 * 计算两条序列的皮尔逊相关系数。
 * @param x 第一条序列。
 * @param y 第二条序列。
 * @returns 相关系数，样本不足时返回 null。
 */
function computeCorrelation(x: number[], y: number[]): number | null {
  if (x.length !== y.length || x.length < 2) {
    return null;
  }

  const meanX = x.reduce((sum, value) => sum + value, 0) / x.length;
  const meanY = y.reduce((sum, value) => sum + value, 0) / y.length;
  let covariance = 0;
  let varianceX = 0;
  let varianceY = 0;

  for (let index = 0; index < x.length; index += 1) {
    const centeredX = x[index]! - meanX;
    const centeredY = y[index]! - meanY;
    covariance += centeredX * centeredY;
    varianceX += centeredX * centeredX;
    varianceY += centeredY * centeredY;
  }

  if (varianceX === 0 || varianceY === 0) {
    return null;
  }

  return covariance / Math.sqrt(varianceX * varianceY);
}

/**
 * 计算最新 spread 的 z-score，衡量当前背离是否偏离历史中枢。
 * @param values spread 序列。
 * @returns z-score，样本不足或无波动时返回 null。
 */
function computeLatestZScore(values: number[]): number | null {
  if (values.length < 2) {
    return null;
  }

  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  const variance = values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / values.length;
  const std = Math.sqrt(variance);

  if (std === 0) {
    return null;
  }

  return (values[values.length - 1]! - mean) / std;
}

/**
 * 生成配对分析的定性结论，突出 widening / tightening 与均值回归风险。
 * @param latestSpread 最新 spread。
 * @param previousSpread 前一期 spread。
 * @param zScore 最新 z-score。
 * @returns 研究风格的 regime 说明。
 */
function describePairRegime(latestSpread: number | null, previousSpread: number | null, zScore: number | null): string {
  if (latestSpread === null) {
    return "Single-series trend";
  }

  const direction =
    previousSpread === null ? "New spread print" : latestSpread > previousSpread ? "Widening" : latestSpread < previousSpread ? "Tightening" : "Stable";

  if (zScore === null) {
    return `${direction} near limited sample`;
  }

  if (zScore >= 1) {
    return `${direction} with stretched divergence`;
  }

  if (zScore <= -1) {
    return `${direction} after compression`;
  }

  return `${direction} around fair range`;
}

/**
 * 生成配对分析顶部统计卡。
 * @param section 宏观配对区块。
 * @returns 统计项集合。
 */
export function buildPairStats(section: MacroComparisonSection): PairStat[] {
  const overlap = buildOverlappingTimeline(section);
  const primarySeries = overlap.map((point) => point.primary!).filter((value) => Number.isFinite(value));
  const secondarySeries = overlap.map((point) => point.secondary!).filter((value) => Number.isFinite(value));
  const deltaSeries = section.deltaPoints.map((point) => point.value);
  const correlation = computeCorrelation(primarySeries, secondarySeries);
  const zScore = computeLatestZScore(deltaSeries);
  const latestSpread = deltaSeries.length ? deltaSeries[deltaSeries.length - 1]! : null;
  const previousSpread = deltaSeries.length > 1 ? deltaSeries[deltaSeries.length - 2]! : null;
  const overlapPrimaryRebased = rebaseTo100(primarySeries);
  const overlapSecondaryRebased = rebaseTo100(secondarySeries);
  const primaryRelativeMove =
    overlapPrimaryRebased.length > 1 ? `${(overlapPrimaryRebased[overlapPrimaryRebased.length - 1]! - 100).toFixed(1)}%` : "n/a";
  const secondaryRelativeMove =
    overlapSecondaryRebased.length > 1 ? `${(overlapSecondaryRebased[overlapSecondaryRebased.length - 1]! - 100).toFixed(1)}%` : "n/a";

  return [
    {
      label: "Pair correlation",
      value: correlation === null ? "Insufficient overlap" : correlation.toFixed(2),
    },
    {
      label: "Spread z-score",
      value: zScore === null ? "n/a" : zScore.toFixed(2),
    },
    {
      label: "Primary relative move",
      value: primaryRelativeMove,
    },
    {
      label: "Secondary relative move",
      value: section.secondary ? secondaryRelativeMove : "Single series",
    },
    {
      label: "Regime",
      value: describePairRegime(latestSpread, previousSpread, zScore),
    },
  ];
}

/**
 * 构建配对相对走势（Base=100）图，适合比较不同量纲指标的相对强弱。
 * @param section 宏观配对区块。
 * @returns ECharts 配置；若无配对则返回 null。
 */
export function buildRelativePerformanceOption(section: MacroComparisonSection): EChartsOption | null {
  if (!section.secondary) {
    return null;
  }

  const overlap = buildOverlappingTimeline(section);
  if (overlap.length < 2) {
    return null;
  }

  const labels = overlap.map((point) => point.periodLabel);
  const primaryValues = overlap.map((point) => point.primary!);
  const secondaryValues = overlap.map((point) => point.secondary!);

  return {
    animation: false,
    color: ["#0f172a", "#2563eb"],
    grid: { left: 48, right: 20, top: 28, bottom: 32 },
    legend: {
      top: 0,
      right: 8,
      textStyle: { color: "#475569", fontSize: 12 },
      data: [section.primary.label, section.secondary.label],
    },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "line" },
    },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: labels,
      axisLabel: { color: "#64748b", fontSize: 11 },
      axisLine: { lineStyle: { color: "#cbd5e1" } },
    },
    yAxis: {
      type: "value",
      axisLabel: {
        color: "#64748b",
        formatter: (value: number) => `${value.toFixed(0)}`,
      },
      splitLine: { lineStyle: { color: "#e2e8f0" } },
    },
    series: [
      {
        name: section.primary.label,
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 6,
        data: rebaseTo100(primaryValues),
        lineStyle: { width: 3 },
      },
      {
        name: section.secondary.label,
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 6,
        data: rebaseTo100(secondaryValues),
        lineStyle: { width: 3 },
      },
    ],
  };
}

/**
 * 构建 spread / divergence 监控图。
 * @param section 宏观配对区块。
 * @returns ECharts 配置；若无有效 spread 则返回 null。
 */
export function buildSpreadMonitorOption(section: MacroComparisonSection): EChartsOption | null {
  if (!section.deltaPoints.length) {
    return null;
  }

  return {
    animation: false,
    color: ["#b45309"],
    grid: { left: 48, right: 20, top: 24, bottom: 32 },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
    },
    xAxis: {
      type: "category",
      data: section.deltaPoints.map((point) => point.periodLabel),
      axisLabel: { color: "#64748b", fontSize: 11 },
      axisLine: { lineStyle: { color: "#cbd5e1" } },
    },
    yAxis: {
      type: "value",
      axisLabel: {
        color: "#64748b",
        formatter: (value: number) => formatUnitValue(value, section.primary.unit),
      },
      splitLine: { lineStyle: { color: "#e2e8f0" } },
    },
    series: [
      {
        name: section.deltaLabel,
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 6,
        data: section.deltaPoints.map((point) => point.value),
        areaStyle: { color: "rgba(180, 83, 9, 0.12)" },
        lineStyle: { width: 3 },
        markLine: {
          silent: true,
          symbol: "none",
          lineStyle: { color: "#94a3b8", type: "dashed" },
          data: [{ yAxis: 0 }],
        },
      },
    ],
  };
}

/**
 * 构建单条原始序列图，用于 pair 下钻时查看绝对水平变化。
 * @param indicator 指标视图。
 * @returns ECharts 配置；无历史时返回 null。
 */
export function buildRawSeriesOption(indicator: MacroIndicatorView): EChartsOption | null {
  if (indicator.points.length < 2) {
    return null;
  }

  return {
    animation: false,
    color: ["#0f172a"],
    grid: { left: 48, right: 20, top: 24, bottom: 32 },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "line" },
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
        symbolSize: 6,
        data: indicator.points.map((point) => point.value),
        lineStyle: { width: 3 },
        areaStyle: { color: "rgba(15, 23, 42, 0.08)" },
      },
    ],
  };
}

/**
 * 生成单指标原始序列辅助统计。
 * @param indicator 指标视图。
 * @returns 指标统计项。
 */
export function buildRawSeriesStats(indicator: MacroIndicatorView): PairStat[] {
  if (!indicator.points.length) {
    return [
      { label: "Latest print", value: indicator.latestValue },
      { label: "Sample depth", value: "0 observations" },
    ];
  }

  const values = indicator.points.map((point) => point.value);
  const latest = values[values.length - 1]!;
  const first = values[0]!;
  const change = latest - first;
  const sign = change > 0 ? "+" : "";

  return [
    { label: "Latest print", value: indicator.latestValue },
    { label: "Sample depth", value: `${indicator.points.length} observations` },
    { label: "Window change", value: `${sign}${formatUnitValue(change, indicator.unit)}` },
  ];
}
