import { FunnelIcon, PencilSquareIcon, PlusIcon, XMarkIcon } from "@heroicons/react/24/outline";
import { useEffect, useState, type FormEvent } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { EventTimelineCanvas } from "../features/event-outlook/components/event-timeline-canvas";
import { useCreateEventOutlookEventMutation, useUpdateEventOutlookEventMutation } from "../features/event-outlook/hooks/use-event-outlook-mutations";
import { useEventOutlookModuleQuery } from "../features/event-outlook/hooks/use-event-outlook-module-query";
import {
  EVENT_OUTLOOK_TABS,
  type EventOutlookCategory,
  type EventOutlookEvent,
} from "../features/event-outlook/model/event-outlook.types";
import { buildModuleTabSearchParams, resolveModuleTab } from "../shared/lib/module-tabs";
import { LastUpdatedBadge } from "../shared/ui/last-updated-badge";
import { ModulePageFrame } from "../shared/ui/module-page-frame";
import { ModuleTabBar } from "../shared/ui/module-tab-bar";
import { ErrorPanelState, LoadingPanelState } from "../shared/ui/panel-state";

type EventFormState = {
  event_date: string;
  title: string;
  summary: string;
  category: EventOutlookCategory;
  source_name: string;
  source_url: string;
};

/**
 * 生成浏览器本地时区下的今日日期。
 * @returns YYYY-MM-DD 格式的本地日期。
 */
function todayIsoDate(): string {
  // 使用浏览器本地时区生成日期，避免界面日期受 UTC 偏移影响。
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/**
 * 计算指定日期向后一年的日期。
 * @param value YYYY-MM-DD 格式的起始日期。
 * @returns 起始日期一年后的 YYYY-MM-DD 日期。
 */
function addOneYear(value: string): string {
  // 自定义范围默认向后一年，保持与后端未来一年窗口一致。
  const next = new Date(`${value}T00:00:00`);
  next.setFullYear(next.getFullYear() + 1);
  const year = next.getFullYear();
  const month = String(next.getMonth() + 1).padStart(2, "0");
  const day = String(next.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

const defaultEventForm: EventFormState = {
  event_date: "",
  title: "",
  summary: "",
  category: "technology",
  source_name: "manual",
  source_url: "",
};

/**
 * 渲染事件展望页面，提供时间轴筛选、录入与编辑。
 * @returns Event Outlook 页面组件。
 */
export function EventOutlookPage() {
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = resolveModuleTab(searchParams.get("tab"), EVENT_OUTLOOK_TABS, "domestic");
  const initialStartDate = searchParams.get("start_date") ?? todayIsoDate();
  const initialEndDate = searchParams.get("end_date") ?? addOneYear(initialStartDate);
  const [startDate, setStartDate] = useState(initialStartDate);
  const [endDate, setEndDate] = useState(initialEndDate);
  const [appliedStartDate, setAppliedStartDate] = useState(initialStartDate);
  const [appliedEndDate, setAppliedEndDate] = useState(initialEndDate);
  const [eventForm, setEventForm] = useState<EventFormState>(defaultEventForm);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [editingEvent, setEditingEvent] = useState<EventOutlookEvent | null>(null);
  const [editForm, setEditForm] = useState({ title: "", summary: "" });
  const query = useEventOutlookModuleQuery({
    region: activeTab,
    startDate: appliedStartDate,
    endDate: appliedEndDate,
    refreshToken: 0,
  });
  const createMutation = useCreateEventOutlookEventMutation();
  const updateMutation = useUpdateEventOutlookEventMutation();

  useEffect(() => {
    if (searchParams.get("tab") === activeTab) return;
    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.set("tab", activeTab);
    setSearchParams(nextSearchParams, { replace: true });
  }, [activeTab, searchParams, setSearchParams]);

  const toolbar = (
    <ModuleTabBar
      activeTab={activeTab}
      ariaLabel="Event Outlook category tabs"
      pathname={location.pathname}
      searchParams={buildModuleTabSearchParams(searchParams, activeTab)}
      storageKey="event-outlook-tab-order"
      tabs={EVENT_OUTLOOK_TABS}
    />
  );

  /**
   * 应用画布工具栏中的时间范围筛选。
   * @param nextStart 下一次查询的起始日期。
   * @param nextEnd 下一次查询的结束日期。
   * @returns 无返回值。
   */
  function applyRange(nextStart = startDate, nextEnd = endDate) {
    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.set("tab", activeTab);
    nextSearchParams.set("start_date", nextStart);
    nextSearchParams.set("end_date", nextEnd);
    setSearchParams(nextSearchParams);
    setStartDate(nextStart);
    setEndDate(nextEnd);
    setAppliedStartDate(nextStart);
    setAppliedEndDate(nextEnd);
  }

  /**
   * 处理时间范围筛选表单提交。
   * @param event 表单提交事件。
   * @returns 无返回值。
   */
  function handleRangeSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    applyRange();
  }

  /**
   * 提交新增事件表单并在成功后关闭弹窗。
   * @param event 表单提交事件。
   * @returns 无返回值。
   */
  function handleCreateEvent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createMutation.mutate(
      {
        region: activeTab,
        ...eventForm,
      },
      {
        onSuccess: () => {
          setEventForm(defaultEventForm);
          setIsCreateDialogOpen(false);
        },
      },
    );
  }

  /**
   * 打开编辑弹窗并填充当前事件内容。
   * @param event 被选中的时间轴事件。
   * @returns 无返回值。
   */
  function beginEditEvent(event: EventOutlookEvent) {
    setEditingEvent(event);
    setEditForm({ title: event.title, summary: event.summary });
  }

  /**
   * 提交事件编辑表单并在成功后关闭弹窗。
   * @param event 表单提交事件。
   * @returns 无返回值。
   */
  function handleUpdateEvent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingEvent) return;
    updateMutation.mutate(
      {
        id: editingEvent.id,
        title: editForm.title,
        summary: editForm.summary,
      },
      {
        onSuccess: () => {
          setEditingEvent(null);
        },
      },
    );
  }

  if (query.isPending) {
    return (
      <ModulePageFrame
        contentLayoutClassName="grid gap-6"
        description="Forward calendar for technology, policy, and finance events."
        lastUpdated={null}
        main={<LoadingPanelState title="Loading event outlook" description="Fetching timeline events and local range settings." />}
        title="Event Outlook"
        toolbar={toolbar}
      />
    );
  }

  if (query.isError || !query.data) {
    return (
      <ModulePageFrame
        contentLayoutClassName="grid gap-6"
        description="Forward calendar for technology, policy, and finance events."
        lastUpdated={null}
        main={<ErrorPanelState title="Event outlook unavailable" description="The timeline payload could not be loaded." />}
        title="Event Outlook"
        toolbar={toolbar}
      />
    );
  }

  return (
    <ModulePageFrame
      contentLayoutClassName="grid gap-6"
      description={query.data.module.description}
      lastUpdated={<LastUpdatedBadge value={query.data.generated_at} />}
      main={
        <>
          <EventTimelineCanvas
            endDate={appliedEndDate}
            events={query.data.events}
            onSelectEvent={beginEditEvent}
            startDate={appliedStartDate}
            toolbar={
              <>
                <div className="grid gap-1">
                  <strong className="text-base font-semibold leading-tight text-slate-950">Event Outlook</strong>
                  <span className="text-xs text-slate-500">2026 重点事件观察</span>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <form
                    aria-label="时间范围过滤器"
                    className="flex flex-wrap items-center gap-2 rounded-full border border-slate-200 bg-white p-1.5 shadow-sm"
                    onSubmit={handleRangeSubmit}
                  >
                    <label className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500">
                      起始日期
                      <input
                        className="h-8 w-36 rounded-full border border-slate-200 px-3 text-xs font-medium text-slate-900"
                        onChange={(event) => setStartDate(event.target.value)}
                        type="date"
                        value={startDate}
                      />
                    </label>
                    <label className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500">
                      结束日期
                      <input
                        className="h-8 w-36 rounded-full border border-slate-200 px-3 text-xs font-medium text-slate-900"
                        onChange={(event) => setEndDate(event.target.value)}
                        type="date"
                        value={endDate}
                      />
                    </label>
                    <button
                      className="inline-flex h-8 items-center gap-1.5 rounded-full bg-slate-200 px-3 text-xs font-semibold text-slate-700 hover:bg-slate-300"
                      type="submit"
                    >
                      <FunnelIcon aria-hidden="true" className="h-4 w-4" />
                      筛选
                    </button>
                  </form>
                  <button
                    aria-label="新增事件"
                    className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-slate-950 text-white shadow-sm hover:bg-slate-800"
                    onClick={() => setIsCreateDialogOpen(true)}
                    type="button"
                  >
                    <PlusIcon aria-hidden="true" className="h-5 w-5" />
                  </button>
                </div>
              </>
            }
          />

          {isCreateDialogOpen ? (
            <div aria-labelledby="create-event-title" aria-modal="true" className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4" role="dialog">
              <form className="w-full max-w-lg rounded-lg border border-slate-200 bg-white shadow-2xl" onSubmit={handleCreateEvent}>
                <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
                  <h3 className="text-base font-semibold text-slate-950" id="create-event-title">新增时间轴事件</h3>
                  <button
                    aria-label="关闭弹窗"
                    className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-slate-600 hover:bg-slate-200"
                    onClick={() => setIsCreateDialogOpen(false)}
                    type="button"
                  >
                    <XMarkIcon aria-hidden="true" className="h-4 w-4" />
                  </button>
                </div>
                <div className="grid gap-3 p-5">
                  <label className="grid gap-1 text-sm font-medium text-slate-700">
                    事件日期
                    <input
                      className="h-10 rounded-md border border-slate-200 px-3 text-sm text-slate-900"
                      onChange={(event) => setEventForm((current) => ({ ...current, event_date: event.target.value }))}
                      required
                      type="date"
                      value={eventForm.event_date}
                    />
                  </label>
                  <label className="grid gap-1 text-sm font-medium text-slate-700">
                    事件标题
                    <input
                      className="h-10 rounded-md border border-slate-200 px-3 text-sm text-slate-900"
                      onChange={(event) => setEventForm((current) => ({ ...current, title: event.target.value }))}
                      required
                      value={eventForm.title}
                    />
                  </label>
                  <label className="grid gap-1 text-sm font-medium text-slate-700">
                    分类
                    <select
                      className="h-10 rounded-md border border-slate-200 px-3 text-sm text-slate-900"
                      onChange={(event) => setEventForm((current) => ({ ...current, category: event.target.value as EventOutlookCategory }))}
                      value={eventForm.category}
                    >
                      <option value="technology">Technology</option>
                      <option value="politics">Politics</option>
                      <option value="finance">Finance</option>
                    </select>
                  </label>
                  <label className="grid gap-1 text-sm font-medium text-slate-700">
                    事件摘要
                    <textarea
                      className="min-h-24 rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900"
                      onChange={(event) => setEventForm((current) => ({ ...current, summary: event.target.value }))}
                      required
                      value={eventForm.summary}
                    />
                  </label>
                  <button
                    className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-slate-900 px-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400"
                    disabled={createMutation.isPending}
                    type="submit"
                  >
                    <PlusIcon aria-hidden="true" className="h-4 w-4" />
                    保存事件
                  </button>
                </div>
              </form>
            </div>
          ) : null}

          {editingEvent ? (
            <div aria-labelledby="edit-event-title" aria-modal="true" className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4" role="dialog">
              <form className="w-full max-w-lg rounded-lg border border-slate-200 bg-white shadow-2xl" onSubmit={handleUpdateEvent}>
                <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
                  <h3 className="text-base font-semibold text-slate-950" id="edit-event-title">编辑时间轴事件</h3>
                  <button
                    aria-label="关闭弹窗"
                    className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-slate-600 hover:bg-slate-200"
                    onClick={() => setEditingEvent(null)}
                    type="button"
                  >
                    <XMarkIcon aria-hidden="true" className="h-4 w-4" />
                  </button>
                </div>
                <div className="grid gap-3 p-5">
                  <label className="grid gap-1 text-sm font-medium text-slate-700">
                    事件标题
                    <input
                      className="h-10 rounded-md border border-slate-200 px-3 text-sm text-slate-900"
                      onChange={(event) => setEditForm((current) => ({ ...current, title: event.target.value }))}
                      required
                      value={editForm.title}
                    />
                  </label>
                  <label className="grid gap-1 text-sm font-medium text-slate-700">
                    事件摘要
                    <textarea
                      className="min-h-24 rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900"
                      onChange={(event) => setEditForm((current) => ({ ...current, summary: event.target.value }))}
                      required
                      value={editForm.summary}
                    />
                  </label>
                  <button
                    className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-slate-900 px-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400"
                    disabled={updateMutation.isPending}
                    type="submit"
                  >
                    <PencilSquareIcon aria-hidden="true" className="h-4 w-4" />
                    保存修改
                  </button>
                </div>
              </form>
            </div>
          ) : null}
        </>
      }
      title="Event Outlook"
      toolbar={toolbar}
    />
  );
}
