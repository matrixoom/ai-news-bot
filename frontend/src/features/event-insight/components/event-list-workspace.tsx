import { ArrowUpTrayIcon, QueueListIcon } from "@heroicons/react/24/outline";
import { useEffect, useMemo, useState } from "react";
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

  return (
    <EventInsightShell
      title="事件列表"
      description="集中处理从研报、资讯和人工材料中提取的结构化事件，快速判断可信度、主题归属与后续动作。"
      actions={
        <>
          <button className="rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50" type="button">
            <QueueListIcon aria-hidden="true" className="mr-1 inline h-4 w-4" />批量处理
          </button>
          <button className="rounded-md bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700" type="button">
            <ArrowUpTrayIcon aria-hidden="true" className="mr-1 inline h-4 w-4" />导入材料
          </button>
        </>
      }
    >
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

        <InsightPanel aside={<button className="text-xs font-semibold text-blue-700" type="button">编辑</button>} title="事件详情">
          <EventDetailDrawer event={selectedEvent} isError={detailQuery.isError} isLoading={detailQuery.isLoading} />
        </InsightPanel>
      </div>
    </EventInsightShell>
  );
}
