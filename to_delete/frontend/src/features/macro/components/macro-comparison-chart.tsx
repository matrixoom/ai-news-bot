import { EChartsSurface } from "./echarts-surface";
import {
  buildPairStats,
  buildRelativePerformanceOption,
  buildSpreadMonitorOption,
} from "../model/macro-pair-analytics";
import type { MacroComparisonSection } from "../model/macro-module.types";

type MacroComparisonChartProps = {
  section: MacroComparisonSection;
};

/**
 * 渲染配对研究图表，聚焦相对强弱、背离与均值回归风险。
 * @param props 宏观配对区块。
 * @returns 量化风格的配对图表组。
 */
export function MacroComparisonChart({ section }: MacroComparisonChartProps) {
  const stats = buildPairStats(section);
  const relativeOption = buildRelativePerformanceOption(section);
  const spreadOption = buildSpreadMonitorOption(section);

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-5">
        {stats.map((stat) => (
          <ChartStat key={`${section.key}-${stat.label}`} label={stat.label} value={stat.value} />
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]">
        <EChartsSurface
          ariaLabel={`${section.title} relative performance chart`}
          description={
            section.secondary
              ? "Rebased to 100 at the first overlapping observation so relative leadership shifts are immediately visible."
              : "Single-series fallback for macro blocks that do not carry a secondary leg."
          }
          option={relativeOption ?? spreadOption ?? undefined}
          title={section.secondary ? "Relative performance" : "Primary trend"}
        />
        <EChartsSurface
          ariaLabel={`${section.title} spread chart`}
          description={
            section.secondary
              ? "Tracks spread direction and whether the pair is widening, tightening, or reverting toward its historical center."
              : "No spread leg exists for this block, so the panel remains intentionally empty."
          }
          option={section.secondary ? spreadOption ?? undefined : undefined}
          title={section.secondary ? "Spread monitor" : "Spread unavailable"}
        />
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <ChartStat label="Primary cadence" value={section.primary.frequency} />
        <ChartStat label="Secondary cadence" value={section.secondary?.frequency ?? "Single series"} />
        <ChartStat label="Gap metric" value={section.secondary ? section.deltaLabel : "n/a"} />
      </div>
    </div>
  );
}

/**
 * 渲染图表辅助指标卡。
 * @param props 指标标签和值。
 * @returns 小型统计卡片。
 */
function ChartStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-medium text-slate-950">{value}</p>
    </div>
  );
}
