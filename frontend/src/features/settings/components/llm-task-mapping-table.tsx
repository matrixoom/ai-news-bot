import type { LlmTaskConfig } from "../model/llm-settings.types";

const taskLabels: Record<string, string> = {
  event_extraction: "材料事件抽取",
  event_deduplication: "事件聚类与去重",
  topic_summary: "主题摘要",
  relation_suggestion: "事件关系建议",
};

/** 渲染任务默认模型映射。 */
export function LlmTaskMappingTable({ taskConfigs }: { taskConfigs: LlmTaskConfig[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-[720px] table-fixed text-left text-xs">
        <thead className="bg-slate-50 text-slate-500">
          <tr><th className="px-4 py-3">任务类型</th><th className="px-4 py-3">默认配置</th><th className="px-4 py-3">模型参数</th></tr>
        </thead>
        <tbody>
          {taskConfigs.map((item) => (
            <tr className="border-t border-slate-100" key={item.taskType}>
              <td className="px-4 py-3 text-slate-700">{taskLabels[item.taskType] ?? item.taskType}</td>
              <td className="px-4 py-3 text-slate-700">{item.providerName}</td>
              <td className="px-4 py-3 text-slate-500">{item.modelName || "使用 provider 默认模型"} · temp {item.temperature}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
