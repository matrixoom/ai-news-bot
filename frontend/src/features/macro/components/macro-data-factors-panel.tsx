import type { EChartsOption } from "echarts";
import { EChartsSurface } from "./echarts-surface";
import type { MacroModuleViewModel } from "../model/macro-module.types";

type MacroDataFactorsPanelProps = {
  model: MacroModuleViewModel;
};

/**
 * 渲染 Macro 数据因子主视图。
 * @param props 包含适配后的 Macro 视图模型。
 * @returns 数据因子趋势图、指标摘要和历史数据表。
 */
export function MacroDataFactorsPanel({ model }: MacroDataFactorsPanelProps) {
  const { dataFactors } = model;
  const selectedFactor =
    dataFactors.factors.find((factor) => factor.factorCode === dataFactors.defaultFactorCode) ??
    dataFactors.factors[0];
  const selectedSeries = selectedFactor
    ? dataFactors.series.find((series) => series.factorCode === selectedFactor.factorCode)
    : undefined;

  return (
    <section className="space-y-4">
      <header className="rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Data factors</p>
        <h3 className="mt-2 text-xl font-semibold text-slate-950">数据因子</h3>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          每个指标独立呈现趋势、来源、频率和质量状态；预测模型后续基于这些数据因子构建。
        </p>
      </header>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {dataFactors.factors.map((factor) => (
          <article key={factor.factorCode} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h4 className="text-base font-semibold text-slate-950">{factor.factorLabel}</h4>
                <p className="mt-1 text-xs text-slate-500">{factor.frequency}</p>
              </div>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-medium text-slate-600">
                {factor.status}
              </span>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-600">{factor.description}</p>
          </article>
        ))}
      </div>

      {selectedFactor ? (
        <article className="rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h3 className="text-xl font-semibold text-slate-950">{selectedFactor.factorLabel}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{selectedFactor.description}</p>
            </div>
            <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600">
              {selectedFactor.storageTable}
            </span>
          </div>
          <div className="mt-5">
            <EChartsSurface
              ariaLabel={`${selectedFactor.factorLabel} trend chart`}
              description={`${selectedFactor.factorLabel} 的历史趋势图。`}
              option={buildFactorChartOption(selectedSeries)}
              title={`${selectedFactor.factorLabel} 趋势`}
            />
          </div>
        </article>
      ) : null}

      <section className="overflow-hidden rounded-[1.5rem] border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 p-5">
          <h3 className="text-lg font-semibold text-slate-950">历史数据表</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-100 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
              <tr>
                <th className="px-4 py-3">指标</th>
                <th className="px-4 py-3">周期</th>
                <th className="px-4 py-3">维度</th>
                <th className="px-4 py-3">数值</th>
                <th className="px-4 py-3">来源</th>
                <th className="px-4 py-3">状态</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {dataFactors.tableRows.map((row) => (
                <tr key={`${row.factorCode}-${row.periodLabel}-${row.dimension}`}>
                  <td className="px-4 py-3 font-medium text-slate-950">{row.factorLabel}</td>
                  <td className="px-4 py-3 text-slate-600">{row.periodLabel}</td>
                  <td className="px-4 py-3 text-slate-600">{row.dimension}</td>
                  <td className="px-4 py-3 text-slate-950">{row.value}</td>
                  <td className="px-4 py-3 text-slate-600">{row.sourceLabel}</td>
                  <td className="px-4 py-3 text-slate-600">{row.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}

/**
 * 将单个数据因子序列转换为 ECharts 折线图配置。
 * @param series 当前选中因子的历史序列，缺失或为空时不绘制图表。
 * @returns ECharts 配置；无真实观测点时返回 undefined。
 */
function buildFactorChartOption(series?: MacroModuleViewModel["dataFactors"]["series"][number]): EChartsOption | undefined {
  if (!series || !series.points.length) {
    return undefined;
  }

  return {
    grid: { left: 48, right: 24, top: 36, bottom: 48 },
    tooltip: { trigger: "axis" },
    legend: { top: 0, data: [series.label] },
    xAxis: {
      type: "category",
      data: series.points.map((point) => point.periodLabel),
    },
    yAxis: {
      type: "value",
      name: series.unit,
    },
    series: [
      {
        name: series.label,
        type: "line",
        smooth: true,
        data: series.points.map((point) => point.value),
      },
    ],
  };
}
