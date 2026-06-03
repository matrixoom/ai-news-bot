import { ArrowUpTrayIcon, QueueListIcon } from "@heroicons/react/24/outline";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { importEventInsightDocument } from "../api/import-document";
import { runEventInsightBatchAction } from "../api/run-event-batch-action";
import { updateEventInsightEvent } from "../api/update-event";
import { useEventDetailQuery } from "../hooks/use-event-detail-query";
import { useEventInsightEventsQuery } from "../hooks/use-event-insight-events-query";
import type { EventInsightEventsQuery } from "../model/event-insight.types";
import { EventDetailDrawer } from "./event-detail-drawer";
import { EventFilterBar } from "./event-filter-bar";
import { EventInsightShell, InsightPanel } from "./event-insight-shell";
import { EventTable } from "./event-table";

/** 渲染真实 API 驱动的事件列表工作台。 */
export function EventListWorkspace() {
  const [filters, setFilters] = useState<EventInsightEventsQuery>({ page: 1, pageSize: 20, status: "active" });
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [actionMessage, setActionMessage] = useState("");
  const queryClient = useQueryClient();
  const listQuery = useEventInsightEventsQuery(filters);
  const events = listQuery.data?.items ?? [];
  const detailQuery = useEventDetailQuery(selectedId);
  const selectedEvent = detailQuery.data?.event ?? events.find((event) => event.id === selectedId);
  const totalLabel = useMemo(() => {
    if (listQuery.isLoading) return "正在同步";
    return `共 ${listQuery.data?.total ?? 0} 条 · 真实 API`;
  }, [listQuery.data?.total, listQuery.isLoading]);

  useEffect(() => {
    if (selectedId === null && events.length > 0) {
      setSelectedId(events[0].id);
    }
    if (selectedId !== null && events.length > 0 && !events.some((event) => event.id === selectedId)) {
      setSelectedId(events[0].id);
    }
  }, [events, selectedId]);

  const updateEventMutation = useMutation({
    mutationFn: (payload: { title: string; summary: string }) => {
      if (selectedId === null) throw new Error("event not selected");
      return updateEventInsightEvent(selectedId, { ...payload, reason: "frontend edit" });
    },
    onSuccess: () => {
      setIsEditOpen(false);
      setActionMessage("事件已保存。");
      queryClient.invalidateQueries({ queryKey: ["event-insight-events"] });
      queryClient.invalidateQueries({ queryKey: ["event-insight-event-detail", selectedId] });
    },
  });

  const batchActionMutation = useMutation({
    mutationFn: () => runEventInsightBatchAction({ eventIds: selectedId === null ? [] : [selectedId], action: "ignore", params: { reason: "batch ignore" } }),
    onSuccess: (result) => {
      setActionMessage(`批量操作完成：${result.succeededEventIds.length} 成功，${result.failedItems.length} 失败。`);
      queryClient.invalidateQueries({ queryKey: ["event-insight-events"] });
    },
  });

  const importMutation = useMutation({
    mutationFn: (payload: { title: string; content: string }) => importEventInsightDocument({ mode: "text", title: payload.title, content: payload.content, sourceType: "news" }),
    onSuccess: (result) => {
      setIsImportOpen(false);
      setActionMessage(`导入任务已创建：#${result.jobId}`);
      queryClient.invalidateQueries({ queryKey: ["event-insight-events"] });
    },
  });

  return (
    <EventInsightShell
      title="事件列表"
      description="集中处理从研报、资讯和人工材料中提取的结构化事件，快速判断可信度、主题归属与后续动作。"
      actions={
        <>
          <button className="rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50" disabled={selectedId === null || batchActionMutation.isPending} onClick={() => batchActionMutation.mutate()} type="button">
            <QueueListIcon aria-hidden="true" className="mr-1 inline h-4 w-4" />批量处理
          </button>
          <button className="rounded-md bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700" onClick={() => setIsImportOpen(true)} type="button">
            <ArrowUpTrayIcon aria-hidden="true" className="mr-1 inline h-4 w-4" />导入材料
          </button>
        </>
      }
    >
      {actionMessage ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{actionMessage}</div> : null}
      {isImportOpen ? <ImportDocumentForm isSaving={importMutation.isPending} onCancel={() => setIsImportOpen(false)} onSubmit={(payload) => importMutation.mutate(payload)} /> : null}
      <EventFilterBar keyword={filters.keyword ?? ""} onApply={(nextFilters) => setFilters((current) => ({ ...current, ...nextFilters, page: 1 }))} status={filters.status ?? "active"} />

      <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_340px]">
        <InsightPanel aside={<span className="text-xs text-slate-500">{totalLabel}</span>} title="结构化事件">
          {listQuery.isLoading ? (
            <div className="p-8 text-center text-sm text-slate-500">正在加载事件列表...</div>
          ) : listQuery.isError ? (
            <div className="p-8 text-center text-sm text-rose-600">事件列表加载失败，请稍后重试。</div>
          ) : (
            <EventTable events={events} onSelect={setSelectedId} selectedId={selectedId} />
          )}
        </InsightPanel>

        <InsightPanel aside={<button className="text-xs font-semibold text-blue-700 disabled:text-slate-400" disabled={!selectedEvent} onClick={() => setIsEditOpen(true)} type="button">编辑</button>} title="事件详情">
          <EventDetailDrawer event={selectedEvent} isError={detailQuery.isError} isLoading={detailQuery.isLoading} />
        </InsightPanel>
      </div>
      {isEditOpen && selectedEvent ? <EventEditForm eventTitle={selectedEvent.title} eventSummary={selectedEvent.summary} isSaving={updateEventMutation.isPending} onCancel={() => setIsEditOpen(false)} onSubmit={(payload) => updateEventMutation.mutate(payload)} /> : null}
    </EventInsightShell>
  );
}

type EventEditFormProps = {
  eventTitle: string;
  eventSummary: string;
  isSaving: boolean;
  onCancel: () => void;
  onSubmit: (payload: { title: string; summary: string }) => void;
};

/** 渲染事件编辑表单。 */
function EventEditForm({ eventTitle, eventSummary, isSaving, onCancel, onSubmit }: EventEditFormProps) {
  const [title, setTitle] = useState(eventTitle);
  const [summary, setSummary] = useState(eventSummary);

  /** 提交人工编辑字段。 */
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({ title: title.trim(), summary: summary.trim() });
  }

  return (
    <form className="rounded-lg border border-blue-100 bg-blue-50/50 p-4" onSubmit={handleSubmit}>
      <div className="grid gap-3 md:grid-cols-2">
        <label className="grid gap-2 text-xs font-semibold text-slate-700">
          事件标题
          <input className="h-9 rounded-md border border-slate-300 px-3 font-normal" onChange={(event) => setTitle(event.target.value)} value={title} />
        </label>
        <label className="grid gap-2 text-xs font-semibold text-slate-700 md:col-span-2">
          事件摘要
          <textarea className="min-h-20 rounded-md border border-slate-300 px-3 py-2 font-normal" onChange={(event) => setSummary(event.target.value)} value={summary} />
        </label>
      </div>
      <div className="mt-3 flex justify-end gap-2">
        <button className="rounded-md border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700" onClick={onCancel} type="button">取消</button>
        <button className="rounded-md bg-blue-600 px-3 py-2 text-xs font-semibold text-white" disabled={isSaving} type="submit">保存事件</button>
      </div>
    </form>
  );
}

type ImportDocumentFormProps = {
  isSaving: boolean;
  onCancel: () => void;
  onSubmit: (payload: { title: string; content: string }) => void;
};

/** 渲染文本材料导入表单。 */
function ImportDocumentForm({ isSaving, onCancel, onSubmit }: ImportDocumentFormProps) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  /** 提交文本材料导入请求。 */
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({ title: title.trim(), content: content.trim() });
  }

  return (
    <form className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm" onSubmit={handleSubmit}>
      <div className="grid gap-3 md:grid-cols-2">
        <label className="grid gap-2 text-xs font-semibold text-slate-700">
          材料标题
          <input className="h-9 rounded-md border border-slate-300 px-3 font-normal" onChange={(event) => setTitle(event.target.value)} value={title} />
        </label>
        <label className="grid gap-2 text-xs font-semibold text-slate-700 md:col-span-2">
          材料正文
          <textarea className="min-h-24 rounded-md border border-slate-300 px-3 py-2 font-normal" onChange={(event) => setContent(event.target.value)} value={content} />
        </label>
      </div>
      <div className="mt-3 flex justify-end gap-2">
        <button className="rounded-md border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700" onClick={onCancel} type="button">取消</button>
        <button className="rounded-md bg-blue-600 px-3 py-2 text-xs font-semibold text-white" disabled={isSaving} type="submit">提交导入</button>
      </div>
    </form>
  );
}
