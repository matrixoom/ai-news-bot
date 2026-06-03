import { formatLocalDateTime } from "../../../shared/utils/format-local-date-time";
import type { EventInsightApiEvent } from "../model/event-insight.types";
import { InsightBadge } from "./event-insight-shell";

type EventDetailDrawerProps = {
  event?: EventInsightApiEvent;
  isLoading: boolean;
  isError: boolean;
};

/** 渲染事件详情侧栏。 */
export function EventDetailDrawer({ event, isLoading, isError }: EventDetailDrawerProps) {
  if (isLoading) {
    return <div className="p-4 text-sm text-slate-500">正在加载事件详情...</div>;
  }
  if (isError) {
    return <div className="p-4 text-sm text-rose-600">事件详情加载失败，请稍后重试。</div>;
  }
  if (!event) {
    return <div className="p-4 text-sm text-slate-500">请选择一个事件查看证据链。</div>;
  }

  return (
    <div className="space-y-4 p-4">
      <div>
        <h4 className="text-base font-semibold leading-6 text-slate-950">{event.title}</h4>
        <p className="mt-2 text-xs leading-6 text-slate-600">{event.summary}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <InsightBadge tone="green">{Math.round(event.confidenceScore * 100)}% 可信度</InsightBadge>
        <InsightBadge tone="blue">{event.evidenceLevel ?? "C"} 级证据</InsightBadge>
      </div>
      <dl className="grid grid-cols-[76px_1fr] gap-y-2 border-t border-slate-200 pt-3 text-xs leading-5">
        <dt className="text-slate-500">主题</dt>
        <dd className="text-slate-700">{event.topics?.map((topic) => topic.name).join("、") || "未归属"}</dd>
        <dt className="text-slate-500">发生时间</dt>
        <dd className="text-slate-700">{formatLocalDateTime(event.eventTime)}</dd>
        <dt className="text-slate-500">分析状态</dt>
        <dd className="text-slate-700">{event.analysisStatus ?? "未分析"}</dd>
        <dt className="text-slate-500">图谱状态</dt>
        <dd className="text-slate-700">{event.graphStatus ?? "未投影"}</dd>
        <dt className="text-slate-500">关联实体</dt>
        <dd className="text-slate-700">{event.entities?.map((entity) => entity.name).join("、") || "暂无实体"}</dd>
      </dl>
      <div>
        <h5 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">关键证据</h5>
        <div className="space-y-2">
          {(event.evidence ?? []).length > 0 ? (
            event.evidence?.map((item) => (
              <div className="rounded-md border border-slate-200 p-3 text-xs leading-5 text-slate-600" key={item.id}>
                <strong className="block text-slate-950">{item.sourceTitle || "未命名来源"}</strong>
                <span className="mb-1 block text-[11px] text-slate-400">
                  原文位置 {item.startOffset ?? 0}-{item.endOffset ?? 0}
                </span>
                {item.excerpt}
              </div>
            ))
          ) : (
            <div className="rounded-md border border-dashed border-slate-200 p-3 text-xs text-slate-500">暂无证据片段。</div>
          )}
        </div>
      </div>
    </div>
  );
}
