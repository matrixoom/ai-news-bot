import { MacroComparisonCard } from "./macro-comparison-card";
import { EChartsSurface } from "./echarts-surface";
import {
  buildGapMonitorOption,
  buildHistoryCoverageOption,
  countHistoryPoints,
  countIndicatorsWithHistory,
  resolveFreshestPeriodLabel,
} from "../model/macro-chart-options";
import type { MacroModuleViewModel } from "../model/macro-module.types";

type MacroOverviewChartboardProps = {
  model: MacroModuleViewModel;
};

/**
 * 渲染宏观总览图表板，提供覆盖度、差值与样本深度的整体视图。
 * @param props 宏观模块视图模型。
 * @returns 总览分析面板。
 */
export function MacroOverviewChartboard({ model }: MacroOverviewChartboardProps) {
  const indicatorsWithHistory = countIndicatorsWithHistory(model);
  const historyPoints = countHistoryPoints(model);

  return (
    <section className="space-y-4">
      <header className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Overview</p>
            <h3 className="mt-2 text-xl font-semibold text-slate-950">Macro chartboard</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Executive view of pair dispersion, history coverage, and indicator readiness across the macro desk.
            </p>
          </div>
          <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
            {model.comparisonSections.length} pairs
          </span>
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <OverviewStat label="Comparison pairs" value={`${model.comparisonSections.length}`} />
        <OverviewStat label="Tracked indicators" value={`${model.indicators.length}`} />
        <OverviewStat label="Indicators with history" value={`${indicatorsWithHistory}`} />
        <OverviewStat label="Freshest period" value={resolveFreshestPeriodLabel(model)} />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <EChartsSurface
          ariaLabel="Macro gap monitor chart"
          description="Latest spread or gap values by comparison pair, useful for spotting dispersion pressure quickly."
          option={buildGapMonitorOption(model)}
          title="Latest gap monitor"
        />
        <EChartsSurface
          ariaLabel="Macro history coverage chart"
          description={`History depth by indicator. ${historyPoints} total observations are currently mapped into the module.`}
          option={buildHistoryCoverageOption(model)}
          title="History coverage"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {model.comparisonSections.slice(0, 2).map((section) => (
          <MacroComparisonCard key={section.key} section={section} />
        ))}
      </div>
    </section>
  );
}

/**
 * 渲染总览统计卡片。
 * @param props 统计项标签和值。
 * @returns 总览统计卡。
 */
function OverviewStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[1.5rem] border border-slate-200 bg-white px-5 py-4 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">{value}</p>
    </div>
  );
}
