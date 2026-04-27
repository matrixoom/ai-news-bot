import type { MacroModuleViewModel } from "../model/macro-module.types";

type MacroSourceMatrixPanelProps = {
  model: MacroModuleViewModel;
};

/**
 * 渲染 Macro 数据源矩阵页。
 * @param props 包含适配后的 Macro 视图模型。
 * @returns 来源可用性汇总和矩阵表格。
 */
export function MacroSourceMatrixPanel({ model }: MacroSourceMatrixPanelProps) {
  const { sourceMatrix } = model;
  const summaryItems = [
    ["指标数", sourceMatrix.summary.factorCount],
    ["来源数", sourceMatrix.summary.sourceCount],
    ["官方主源", sourceMatrix.summary.officialPrimaryCount],
    ["降级来源", sourceMatrix.summary.degradedCount],
    ["不可用来源", sourceMatrix.summary.unavailableCount],
  ];

  return (
    <section className="space-y-4">
      <header className="rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Source matrix</p>
        <h3 className="mt-2 text-xl font-semibold text-slate-950">数据源矩阵</h3>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          按指标梳理官方源、备选源、可靠性、覆盖范围、字段映射和解析器状态。
        </p>
      </header>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {summaryItems.map(([label, value]) => (
          <div key={String(label)} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-medium text-slate-500">{label}</p>
            <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
          </div>
        ))}
      </div>

      <section className="overflow-hidden rounded-[1.5rem] border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-100 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
              <tr>
                <th className="px-4 py-3">指标</th>
                <th className="px-4 py-3">来源</th>
                <th className="px-4 py-3">角色</th>
                <th className="px-4 py-3">可用性</th>
                <th className="px-4 py-3">可靠性</th>
                <th className="px-4 py-3">频率</th>
                <th className="px-4 py-3">字段映射</th>
                <th className="px-4 py-3">解析器</th>
                <th className="px-4 py-3">说明</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sourceMatrix.rows.map((row) => (
                <tr key={row.matrixId}>
                  <td className="px-4 py-3 font-medium text-slate-950">{row.factorLabel}</td>
                  <td className="px-4 py-3 text-slate-700">{row.sourceLabel}</td>
                  <td className="px-4 py-3 text-slate-600">{row.sourceRole}</td>
                  <td className="px-4 py-3 text-slate-600">{row.availabilityStatus}</td>
                  <td className="px-4 py-3 text-slate-600">{row.reliabilityLevel}</td>
                  <td className="px-4 py-3 text-slate-600">{row.frequency}</td>
                  <td className="px-4 py-3 text-slate-600">{row.fieldMappingStatus}</td>
                  <td className="px-4 py-3 text-slate-600">{row.parserStatus}</td>
                  <td className="max-w-md px-4 py-3 text-slate-600">
                    {row.warningMessage || row.coverageScope}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
