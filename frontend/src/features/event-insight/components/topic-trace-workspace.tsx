import { PlusIcon } from "@heroicons/react/24/outline";
import { formatLocalDateTime } from "../../../shared/utils/format-local-date-time";
import { useTopicTraceQuery } from "../hooks/use-topic-trace-query";
import { EventInsightShell, InsightPanel } from "./event-insight-shell";

/** 渲染主题溯源工作台，返回阶段判断与演进时间线。 */
export function TopicTraceWorkspace() {
  const topicId = 1;
  const traceQuery = useTopicTraceQuery(topicId);
  const trace = traceQuery.data;

  return (
    <EventInsightShell
      title="主题溯源"
      description="按主题还原事件演进路径，查看每个阶段的事实依据、判断变化和后续待验证线索。"
      actions={<><select aria-label="选择主题" className="h-9 rounded-md border border-slate-300 px-3 text-xs text-slate-700"><option>{trace?.topic.name ?? "主题 #1"}</option></select><button className="rounded-md bg-blue-600 px-3 py-2 text-xs font-semibold text-white" type="button"><PlusIcon aria-hidden="true" className="mr-1 inline h-4 w-4" />新建主题</button></>}
    >
      {traceQuery.isLoading ? <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-500">正在加载主题溯源...</div> : null}
      {traceQuery.isError ? <div className="rounded-lg border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">主题溯源加载失败，请检查主题是否存在。</div> : null}
      {trace ? <>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {trace.metrics.map((metric) => <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm" key={metric.label}><span className="text-xs text-slate-500">{metric.label}</span><strong className="mt-2 block text-2xl text-slate-950">{metric.value}</strong><small className={metric.noteTone === "amber" ? "text-amber-600" : "text-emerald-600"}>{metric.note}</small></article>)}
      </div>
      <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_320px]">
        <InsightPanel aside={<span className="text-xs text-slate-500">真实数据</span>} title={`${trace.topic.name} · 演进路径`}>
          <div className="p-4">
            <div className="grid gap-2 md:grid-cols-4">
              {trace.stages.map((stage) => <article className={`min-h-20 border-t-4 p-3 ${stage.active ? "border-blue-600 bg-blue-50" : "border-slate-300 bg-slate-50"}`} key={stage.id}><span className="text-[11px] font-semibold text-slate-500">{stage.label}</span><strong className="mt-2 block text-xs text-slate-800">{stage.title}</strong></article>)}
            </div>
            <div className="mt-4 space-y-3 border-l border-slate-300 pl-5">
              {trace.timeline.length === 0 ? <p className="rounded-md border border-dashed border-slate-300 p-4 text-sm text-slate-500">暂无关联事件。</p> : null}
              {trace.timeline.map((entry) => <article className="relative grid gap-3 rounded-md border border-slate-200 bg-white p-3 md:grid-cols-[132px_1fr]" key={entry.id}><i className="absolute -left-[25px] top-5 h-3 w-3 rounded-full border-2 border-white bg-blue-600 ring-1 ring-blue-600" /><time className="text-xs leading-5 text-slate-500">{formatLocalDateTime(entry.happenedAt)}</time><div><h4 className="text-xs font-semibold text-slate-950">{entry.title}</h4><p className="mt-1 text-xs leading-5 text-slate-500">{entry.summary}</p>{entry.evidence?.[0] ? <p className="mt-2 rounded-md bg-slate-50 p-2 text-[11px] leading-5 text-slate-500">{entry.evidence[0].excerpt}</p> : null}</div></article>)}
            </div>
          </div>
        </InsightPanel>
        <InsightPanel title="阶段判断">
          <div className="space-y-4 p-4">
            <h4 className="text-base font-semibold text-slate-950">{trace.currentJudgement.title}</h4>
            <p className="text-xs leading-6 text-slate-600">{trace.currentJudgement.summary}</p>
            <div className="border-t border-slate-200 pt-3">
              <h5 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">待验证线索</h5>
              {trace.currentJudgement.clues.map((item) => <div className="mb-2 rounded-md border border-slate-200 p-3 text-xs font-semibold text-slate-700" key={item}>{item}</div>)}
            </div>
          </div>
        </InsightPanel>
      </div>
      </> : null}
    </EventInsightShell>
  );
}
