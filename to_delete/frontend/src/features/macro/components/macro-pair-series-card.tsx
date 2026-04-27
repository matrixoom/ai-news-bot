import { EChartsSurface } from "./echarts-surface";
import { buildRawSeriesOption, buildRawSeriesStats } from "../model/macro-pair-analytics";
import type { MacroComparisonSection } from "../model/macro-module.types";

type MacroPairSeriesCardProps = {
  section: MacroComparisonSection;
};

/**
 * 按配对展示底层原始序列，便于查看绝对水平与发布节奏。
 * @param props 宏观配对区块。
 * @returns 配对原始序列卡片。
 */
export function MacroPairSeriesCard({ section }: MacroPairSeriesCardProps) {
  return (
    <article className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Pair structure</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-950">{section.title}</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">{section.description}</p>
        </div>
        <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
          {section.status}
        </span>
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        <RawSeriesPanel
          ariaLabel={`${section.title} primary series chart`}
          indicator={section.primary}
          title="Primary series"
        />
        {section.secondary ? (
          <RawSeriesPanel
            ariaLabel={`${section.title} secondary series chart`}
            indicator={section.secondary}
            title="Secondary series"
          />
        ) : null}
      </div>
    </article>
  );
}

/**
 * 渲染单个指标原始序列和辅助统计。
 * @param props 无障碍名称、指标数据和标题。
 * @returns 原始序列面板。
 */
function RawSeriesPanel({
  ariaLabel,
  indicator,
  title,
}: {
  ariaLabel: string;
  indicator: MacroComparisonSection["primary"];
  title: string;
}) {
  const stats = buildRawSeriesStats(indicator);

  return (
    <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50/70 p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{title}</p>
          <h4 className="mt-2 text-lg font-semibold text-slate-950">{indicator.label}</h4>
          <p className="mt-1 text-sm text-slate-600">{indicator.frequency}</p>
        </div>
        <span className="text-sm font-semibold text-slate-950">{indicator.latestValue}</span>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {stats.map((stat) => (
          <div key={`${indicator.key}-${stat.label}`} className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{stat.label}</p>
            <p className="mt-2 text-sm font-medium text-slate-950">{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="mt-4">
        <EChartsSurface
          ariaLabel={ariaLabel}
          description="Absolute level history for release-by-release review."
          option={buildRawSeriesOption(indicator) ?? undefined}
          title={title}
        />
      </div>
    </div>
  );
}
