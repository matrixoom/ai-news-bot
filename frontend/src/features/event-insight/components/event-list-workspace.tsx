import { ArrowUpTrayIcon, FunnelIcon, QueueListIcon } from "@heroicons/react/24/outline";
import { useState } from "react";
import { formatLocalDateTime } from "../../../shared/utils/format-local-date-time";
import { MOCK_EVENTS } from "../mock/event-insight.mock";
import { EventInsightShell, InsightBadge, InsightPanel } from "./event-insight-shell";

/** 渲染事件列表 Mock 工作台，返回可选择事件的研究台。 */
export function EventListWorkspace() {
  const [selectedId, setSelectedId] = useState(MOCK_EVENTS[0].id);
  const selectedEvent = MOCK_EVENTS.find((event) => event.id === selectedId) ?? MOCK_EVENTS[0];

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
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white p-3">
        <div className="flex flex-wrap gap-2">
          <input aria-label="搜索事件" className="h-9 w-64 rounded-md border border-slate-300 px-3 text-xs text-slate-700" placeholder="搜索事件、公司或主题" />
          {["全部类型", "全部状态", "全部可信度"].map((label) => (
            <select aria-label={label} className="h-9 rounded-md border border-slate-300 px-3 text-xs text-slate-700" key={label}>
              <option>{label}</option>
            </select>
          ))}
        </div>
        <button className="rounded-md bg-slate-900 px-3 py-2 text-xs font-semibold text-white" type="button">
          <FunnelIcon aria-hidden="true" className="mr-1 inline h-4 w-4" />筛选
        </button>
      </div>

      <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_340px]">
        <InsightPanel aside={<span className="text-xs text-slate-500">共 126 条 · Mock 数据</span>} title="结构化事件">
          <div className="overflow-x-auto">
            <table className="min-w-[880px] table-fixed text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-50 text-slate-500">
                <tr><th className="w-[36%] px-3 py-3">事件</th><th className="px-3 py-3">类型</th><th className="px-3 py-3">可信度</th><th className="px-3 py-3">主题</th><th className="px-3 py-3">发生时间</th><th className="px-3 py-3">状态</th></tr>
              </thead>
              <tbody>
                {MOCK_EVENTS.map((event) => (
                  <tr className={`border-b border-slate-100 ${selectedEvent.id === event.id ? "bg-blue-50" : "hover:bg-slate-50"}`} key={event.id}>
                    <td className="px-3 py-3">
                      <button aria-label={`查看 ${event.title}`} className="block text-left" onClick={() => setSelectedId(event.id)} type="button">
                        <strong className="block text-xs text-slate-950">{event.title}</strong>
                        <span className="mt-1 block text-[11px] text-slate-500">{event.sourceSummary}</span>
                      </button>
                    </td>
                    <td className="px-3 py-3"><InsightBadge tone={event.typeTone}>{event.type}</InsightBadge></td>
                    <td className="px-3 py-3"><InsightBadge tone={event.confidenceTone}>{event.confidence}</InsightBadge></td>
                    <td className="px-3 py-3 text-slate-700">{event.topic}</td>
                    <td className="px-3 py-3 text-slate-600">{formatLocalDateTime(event.happenedAt)}</td>
                    <td className="px-3 py-3"><InsightBadge tone={event.statusTone}>{event.status}</InsightBadge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </InsightPanel>

        <InsightPanel aside={<button className="text-xs font-semibold text-blue-700" type="button">编辑</button>} title="事件详情">
          <div className="space-y-4 p-4">
            <div>
              <h4 className="text-base font-semibold leading-6 text-slate-950">{selectedEvent.title}</h4>
              <p className="mt-2 text-xs leading-6 text-slate-600">{selectedEvent.summary}</p>
            </div>
            <div className="flex flex-wrap gap-2"><InsightBadge tone={selectedEvent.confidenceTone}>{selectedEvent.confidence}</InsightBadge><InsightBadge tone={selectedEvent.statusTone}>{selectedEvent.status}</InsightBadge></div>
            <dl className="grid grid-cols-[76px_1fr] gap-y-2 border-t border-slate-200 pt-3 text-xs leading-5">
              <dt className="text-slate-500">主题</dt><dd className="text-slate-700">{selectedEvent.topic}</dd>
              <dt className="text-slate-500">发生时间</dt><dd className="text-slate-700">{formatLocalDateTime(selectedEvent.happenedAt)}</dd>
              <dt className="text-slate-500">关联实体</dt><dd className="text-slate-700">{selectedEvent.entities.join("、")}</dd>
              <dt className="text-slate-500">分析任务</dt><dd className="text-slate-700">{selectedEvent.analysisTask}</dd>
            </dl>
            <div>
              <h5 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">关键证据</h5>
              <div className="space-y-2">{selectedEvent.evidence.map((item) => <div className="rounded-md border border-slate-200 p-3 text-xs leading-5 text-slate-600" key={item.id}><strong className="block text-slate-950">{item.source}</strong>{item.excerpt}</div>)}</div>
            </div>
          </div>
        </InsightPanel>
      </div>
    </EventInsightShell>
  );
}
