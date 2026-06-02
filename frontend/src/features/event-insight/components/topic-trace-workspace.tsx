import { PlusIcon } from "@heroicons/react/24/outline";
import { formatLocalDateTime } from "../../../shared/utils/format-local-date-time";
import { MOCK_TOPIC_METRICS, MOCK_TOPIC_STAGES, MOCK_TOPIC_TIMELINE } from "../mock/event-insight.mock";
import { EventInsightShell, InsightPanel } from "./event-insight-shell";

/** 渲染主题溯源 Mock 工作台，返回阶段判断与演进时间线。 */
export function TopicTraceWorkspace() {
  return (
    <EventInsightShell
      title="主题溯源"
      description="按主题还原事件演进路径，查看每个阶段的事实依据、判断变化和后续待验证线索。"
      actions={<><select aria-label="选择主题" className="h-9 rounded-md border border-slate-300 px-3 text-xs text-slate-700"><option>AI 算力供应链</option></select><button className="rounded-md bg-blue-600 px-3 py-2 text-xs font-semibold text-white" type="button"><PlusIcon aria-hidden="true" className="mr-1 inline h-4 w-4" />新建主题</button></>}
    >
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {MOCK_TOPIC_METRICS.map((metric) => <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm" key={metric.label}><span className="text-xs text-slate-500">{metric.label}</span><strong className="mt-2 block text-2xl text-slate-950">{metric.value}</strong><small className={metric.noteTone === "amber" ? "text-amber-600" : "text-emerald-600"}>{metric.note}</small></article>)}
      </div>
      <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_320px]">
        <InsightPanel aside={<span className="text-xs text-slate-500">Mock 数据</span>} title="AI 算力供应链 · 演进路径">
          <div className="p-4">
            <div className="grid grid-cols-4">
              {MOCK_TOPIC_STAGES.map((stage) => <article className={`min-h-20 border-t-4 p-3 ${stage.active ? "border-blue-600 bg-blue-50" : "border-slate-300 bg-slate-50"}`} key={stage.id}><span className="text-[11px] font-semibold text-slate-500">{stage.label}</span><strong className="mt-2 block text-xs text-slate-800">{stage.title}</strong></article>)}
            </div>
            <div className="mt-4 space-y-3 border-l border-slate-300 pl-5">
              {MOCK_TOPIC_TIMELINE.map((entry) => <article className="relative grid gap-3 rounded-md border border-slate-200 bg-white p-3 md:grid-cols-[132px_1fr]" key={entry.id}><i className="absolute -left-[25px] top-5 h-3 w-3 rounded-full border-2 border-white bg-blue-600 ring-1 ring-blue-600" /><time className="text-xs leading-5 text-slate-500">{formatLocalDateTime(entry.happenedAt)}</time><div><h4 className="text-xs font-semibold text-slate-950">{entry.title}</h4><p className="mt-1 text-xs leading-5 text-slate-500">{entry.summary}</p></div></article>)}
            </div>
          </div>
        </InsightPanel>
        <InsightPanel title="阶段判断">
          <div className="space-y-4 p-4">
            <h4 className="text-base font-semibold text-slate-950">阶段 03：HBM4 提前放量</h4>
            <p className="text-xs leading-6 text-slate-600">当前判断从“供给紧张”进一步细化为“HBM4 提前放量但封装约束未解除”。需要继续跟踪设备交付、客户验证和单位价值量变化。</p>
            <div className="border-t border-slate-200 pt-3">
              <h5 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">待验证线索</h5>
              {["先进封装良率", "设备交付周期", "HBM4 单位价值量"].map((item) => <div className="mb-2 rounded-md border border-slate-200 p-3 text-xs font-semibold text-slate-700" key={item}>{item}</div>)}
            </div>
          </div>
        </InsightPanel>
      </div>
    </EventInsightShell>
  );
}
