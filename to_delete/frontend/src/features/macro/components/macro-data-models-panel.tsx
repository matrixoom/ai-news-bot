import type { MacroModuleViewModel } from "../model/macro-module.types";

type MacroDataModelsPanelProps = {
  model: MacroModuleViewModel;
};

/**
 * 渲染 Macro 数据模型预留页。
 * @param props 包含适配后的 Macro 视图模型。
 * @returns 数据模型预留状态。
 */
export function MacroDataModelsPanel({ model }: MacroDataModelsPanelProps) {
  return (
    <section className="rounded-[1.5rem] border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Data models</p>
      <h3 className="mt-2 text-xl font-semibold text-slate-950">{model.dataModels.label}</h3>
      <p className="mt-3 text-sm leading-6 text-slate-600">
        模型入口已预留，第一阶段不输出预测、方向判断或置信度。
      </p>
      <div className="mt-5 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
        后续可在这里接入房价研判模型、经济周期模型和通胀压力模型。
      </div>
    </section>
  );
}
