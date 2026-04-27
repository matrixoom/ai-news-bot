import { EChartsSurface } from "./echarts-surface";
import {
  buildIndicatorChartOption,
  resolveIndicatorAverage,
  resolveIndicatorDelta,
  resolveIndicatorRange,
} from "../model/macro-chart-options";
import type { MacroIndicatorView } from "../model/macro-module.types";

type MacroIndicatorChartCardProps = {
  indicator: MacroIndicatorView;
};

/**
 * 渲染单指标趋势卡，补充区间、均值与最近变化等分析信息。
 * @param props 指标视图数据。
 * @returns 指标趋势卡片。
 */
export function MacroIndicatorChartCard({ indicator }: MacroIndicatorChartCardProps) {
  return (
    <article className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{indicator.frequency}</p>
          <h4 className="mt-2 text-lg font-semibold text-slate-950">{indicator.label}</h4>
          <p className="mt-2 text-sm leading-6 text-slate-600">{indicator.context}</p>
        </div>
        <div className="text-left sm:text-right">
          <p className="text-2xl font-semibold tracking-tight text-slate-950">{indicator.latestValue}</p>
          <p className="mt-1 text-sm text-slate-500">{indicator.periodLabel}</p>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <IndicatorStat label="Historical range" value={resolveIndicatorRange(indicator)} />
        <IndicatorStat label="Average" value={resolveIndicatorAverage(indicator)} />
        <IndicatorStat label="Latest delta" value={resolveIndicatorDelta(indicator)} />
      </div>

      <div className="mt-5">
        <EChartsSurface
          ariaLabel={`${indicator.label} trend chart`}
          description="Time-series history with the average line overlaid for quick cycle context."
          option={indicator.points.length ? buildIndicatorChartOption(indicator) : undefined}
          title={`${indicator.label} trend`}
        />
      </div>
    </article>
  );
}

/**
 * 渲染指标辅助统计卡片。
 * @param props 指标名称和值。
 * @returns 指标统计卡片。
 */
function IndicatorStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-medium text-slate-950">{value}</p>
    </div>
  );
}
