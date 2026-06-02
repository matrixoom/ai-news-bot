import { PlusIcon, SignalIcon } from "@heroicons/react/24/outline";

const TASK_MAPPINGS = [
  { task: "材料事件抽取", provider: "快速抽取模型", note: "速度优先，失败后降级到主分析模型" },
  { task: "事件聚类与去重", provider: "主分析模型", note: "需要更稳定的语义判断" },
  { task: "主题摘要", provider: "主分析模型", note: "生成阶段判断和待验证线索" },
  { task: "事件关系建议", provider: "主分析模型", note: "仅生成建议，人工确认后生效" },
];

/** 渲染展示型大模型配置工作台，真实保存能力将在统一 LLM Runtime 增量中接入。 */
export function LlmSettingsWorkspace() {
  return (
    <section className="space-y-4">
      <header className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-slate-950">大模型配置</h2>
          <p className="mt-1 max-w-4xl text-sm leading-6 text-slate-500">统一管理事件抽取、聚类、主题摘要和关系判断所使用的模型服务。I1 仅提供页面预览，保存能力将在后续增量接入。</p>
        </div>
        <button className="inline-flex items-center rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-400" disabled type="button">
          <PlusIcon aria-hidden="true" className="mr-1 h-4 w-4" />新增配置
        </button>
      </header>

      <div className="grid gap-3 xl:grid-cols-[290px_minmax(0,1fr)]">
        <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
            <h3 className="text-sm font-semibold text-slate-950">模型服务</h3><span className="text-xs text-slate-500">3 个 Mock 配置</span>
          </header>
          <div className="space-y-1 p-2">
            <button className="w-full rounded-md border border-blue-200 bg-blue-50 p-3 text-left" type="button"><strong className="block text-xs text-slate-950">主分析模型</strong><span className="mt-1 block text-[11px] text-slate-500">OpenAI Compatible · 已启用</span></button>
            <button className="w-full rounded-md border border-transparent p-3 text-left hover:bg-slate-50" type="button"><strong className="block text-xs text-slate-950">快速抽取模型</strong><span className="mt-1 block text-[11px] text-slate-500">OpenAI Compatible · 已启用</span></button>
            <button className="w-full rounded-md border border-transparent p-3 text-left hover:bg-slate-50" type="button"><strong className="block text-xs text-slate-950">本地备用模型</strong><span className="mt-1 block text-[11px] text-slate-500">Ollama Compatible · 未启用</span></button>
          </div>
        </section>

        <div className="space-y-3">
          <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
              <h3 className="text-sm font-semibold text-slate-950">主分析模型</h3><span className="rounded-full bg-amber-100 px-2 py-1 text-[11px] font-semibold text-amber-700">Mock 预览</span>
            </header>
            <div className="p-4">
              <div className="grid gap-4 md:grid-cols-2">
                <label className="grid gap-2 text-xs font-semibold text-slate-700">配置名称<input className="h-9 rounded-md border border-slate-300 px-3 font-normal" readOnly value="主分析模型" /></label>
                <label className="grid gap-2 text-xs font-semibold text-slate-700">服务类型<select className="h-9 rounded-md border border-slate-300 px-3 font-normal" disabled><option>OpenAI Compatible</option></select></label>
                <label className="grid gap-2 text-xs font-semibold text-slate-700 md:col-span-2">Base URL<input className="h-9 rounded-md border border-slate-300 px-3 font-normal" readOnly value="https://api.example.com/v1" /></label>
                <label className="grid gap-2 text-xs font-semibold text-slate-700">模型名称<input className="h-9 rounded-md border border-slate-300 px-3 font-normal" readOnly value="analysis-model-pro" /></label>
                <label className="grid gap-2 text-xs font-semibold text-slate-700">API Key<input className="h-9 rounded-md border border-slate-300 px-3 font-normal" readOnly value="已配置，前端不展示密钥" /></label>
                <label className="grid gap-2 text-xs font-semibold text-slate-700">请求超时<input className="h-9 rounded-md border border-slate-300 px-3 font-normal" readOnly value="90 秒" /></label>
                <label className="grid gap-2 text-xs font-semibold text-slate-700">最大并发<input className="h-9 rounded-md border border-slate-300 px-3 font-normal" readOnly value="4" /></label>
              </div>
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4">
                <span className="inline-flex items-center text-xs font-semibold text-amber-700"><SignalIcon aria-hidden="true" className="mr-1 h-4 w-4" />连接状态将在后续增量接入</span>
                <div className="flex gap-2"><button className="rounded-md border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-400" disabled type="button">测试连接</button><button className="rounded-md bg-slate-300 px-3 py-2 text-xs font-semibold text-white" disabled type="button">保存配置</button></div>
              </div>
            </div>
          </section>

          <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            <header className="border-b border-slate-200 px-4 py-3"><h3 className="text-sm font-semibold text-slate-950">任务默认模型</h3></header>
            <div className="overflow-x-auto">
              <table className="min-w-[720px] table-fixed text-left text-xs">
                <thead className="bg-slate-50 text-slate-500"><tr><th className="px-4 py-3">任务类型</th><th className="px-4 py-3">默认配置</th><th className="px-4 py-3">说明</th></tr></thead>
                <tbody>{TASK_MAPPINGS.map((item) => <tr className="border-t border-slate-100" key={item.task}><td className="px-4 py-3 text-slate-700">{item.task}</td><td className="px-4 py-3 text-slate-700">{item.provider}</td><td className="px-4 py-3 text-slate-500">{item.note}</td></tr>)}</tbody>
              </table>
            </div>
          </section>
        </div>
      </div>
    </section>
  );
}
