import { ArrowPathIcon, PencilSquareIcon, PlusIcon } from "@heroicons/react/24/outline";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { EventTimelineCanvas } from "../features/event-outlook/components/event-timeline-canvas";
import { useCreateEventOutlookEventMutation, useUpdateEventOutlookEventMutation } from "../features/event-outlook/hooks/use-event-outlook-mutations";
import { useEventOutlookModuleQuery } from "../features/event-outlook/hooks/use-event-outlook-module-query";
import {
  EVENT_OUTLOOK_TABS,
  type EventOutlookCategory,
  type EventOutlookEvent,
  type EventOutlookRegion,
  type EventOutlookResolution,
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

function todayIsoDate(): string {
  // 使用浏览器本地时区生成日期，避免界面日期受 UTC 偏移影响。
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

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
  const [resolution, setResolution] = useState<EventOutlookResolution>("week");
  const [refreshToken, setRefreshToken] = useState(0);
  const [eventForm, setEventForm] = useState<EventFormState>(defaultEventForm);
  const [editingEvent, setEditingEvent] = useState<EventOutlookEvent | null>(null);
  const [editForm, setEditForm] = useState({ title: "", summary: "" });
  const query = useEventOutlookModuleQuery({
    region: activeTab,
    startDate: appliedStartDate,
    endDate: appliedEndDate,
    refreshToken,
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

  const eventCounts = useMemo(() => {
    const counts: Record<EventOutlookCategory, number> = { technology: 0, politics: 0, finance: 0 };
    for (const event of query.data?.events ?? []) {
      counts[event.category] += 1;
    }
    return counts;
  }, [query.data?.events]);

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
        },
      },
    );
  }

  function beginEditEvent(event: EventOutlookEvent) {
    setEditingEvent(event);
    setEditForm({ title: event.title, summary: event.summary });
  }

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
      contentLayoutClassName="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_360px]"
      description={query.data.module.description}
      lastUpdated={<LastUpdatedBadge value={query.data.generated_at} />}
      main={
        <div className="space-y-5">
          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
              <div className="flex flex-wrap items-end gap-3">
                <label className="grid gap-1 text-sm font-medium text-slate-700">
                  起始日期
                  <input
                    className="h-10 rounded-md border border-slate-200 px-3 text-sm text-slate-900"
                    onChange={(event) => setStartDate(event.target.value)}
                    type="date"
                    value={startDate}
                  />
                </label>
                <label className="grid gap-1 text-sm font-medium text-slate-700">
                  结束日期
                  <input
                    className="h-10 rounded-md border border-slate-200 px-3 text-sm text-slate-900"
                    onChange={(event) => setEndDate(event.target.value)}
                    type="date"
                    value={endDate}
                  />
                </label>
                <button
                  className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 hover:border-slate-300 hover:text-slate-950"
                  onClick={() => applyRange()}
                  type="button"
                >
                  <PencilSquareIcon aria-hidden="true" className="h-4 w-4" />
                  定位时间范围
                </button>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {query.data.resolution_options.map((option) => (
                  <button
                    key={option.value}
                    aria-pressed={resolution === option.value}
                    className={[
                      "h-9 rounded-md border px-3 text-sm font-medium",
                      resolution === option.value
                        ? "border-slate-900 bg-slate-900 text-white"
                        : "border-slate-200 bg-white text-slate-700 hover:border-slate-300",
                    ].join(" ")}
                    onClick={() => setResolution(option.value)}
                    type="button"
                  >
                    {option.label}
                  </button>
                ))}
                <button
                  className="inline-flex h-9 items-center gap-2 rounded-md border border-sky-200 bg-sky-50 px-3 text-sm font-medium text-sky-700 hover:border-sky-300"
                  onClick={() => setRefreshToken((value) => value + 1)}
                  type="button"
                >
                  <ArrowPathIcon aria-hidden="true" className="h-4 w-4" />
                  刷新
                </button>
              </div>
            </div>
          </div>

          <EventTimelineCanvas
            endDate={appliedEndDate}
            events={query.data.events}
            onRangeChange={(nextStart, nextEnd) => applyRange(nextStart, nextEnd)}
            onSelectEvent={beginEditEvent}
            resolution={resolution}
            startDate={appliedStartDate}
          />
        </div>
      }
      side={
        <div className="space-y-5">
          <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <p className="text-xs font-semibold text-slate-500">Technology</p>
                <p className="mt-1 text-2xl font-semibold text-slate-950">{eventCounts.technology}</p>
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-500">Politics</p>
                <p className="mt-1 text-2xl font-semibold text-slate-950">{eventCounts.politics}</p>
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-500">Finance</p>
                <p className="mt-1 text-2xl font-semibold text-slate-950">{eventCounts.finance}</p>
              </div>
            </div>
          </section>

          <form className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm" onSubmit={handleCreateEvent}>
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-950">
              <PlusIcon aria-hidden="true" className="h-4 w-4" />
              手动录入
            </div>
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
              事件摘要
              <textarea
                className="min-h-24 rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900"
                onChange={(event) => setEventForm((current) => ({ ...current, summary: event.target.value }))}
                required
                value={eventForm.summary}
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
            <button
              className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-slate-900 px-3 text-sm font-semibold text-white"
              disabled={createMutation.isPending}
              type="submit"
            >
              <PlusIcon aria-hidden="true" className="h-4 w-4" />
              保存事件
            </button>
          </form>

          {editingEvent ? (
            <form aria-label="编辑事件" className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm" onSubmit={handleUpdateEvent}>
              <div className="text-sm font-semibold text-slate-950">编辑事件</div>
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
                className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-slate-900 px-3 text-sm font-semibold text-white"
                disabled={updateMutation.isPending}
                type="submit"
              >
                <PencilSquareIcon aria-hidden="true" className="h-4 w-4" />
                保存修改
              </button>
            </form>
          ) : null}

          <section className="space-y-2 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            {query.data.events.map((event) => (
              <button
                key={event.id}
                aria-label={`编辑 ${event.title}`}
                className="block w-full rounded-md border border-slate-100 px-3 py-2 text-left text-sm hover:border-slate-300"
                onClick={() => beginEditEvent(event)}
                type="button"
              >
                <span className="block font-semibold text-slate-900">{event.title}</span>
                <span className="mt-1 block text-xs text-slate-500">{event.event_date}</span>
              </button>
            ))}
          </section>
        </div>
      }
      title="Event Outlook"
      toolbar={toolbar}
    />
  );
}
