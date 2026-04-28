import { ErrorPanelState, LoadingPanelState, EmptyPanelState } from "../shared/ui/panel-state";
import { ModulePageFrame } from "../shared/ui/module-page-frame";
import { LastUpdatedBadge } from "../shared/ui/last-updated-badge";
import { EventWindowCard } from "../features/events/components/event-window-card";
import { EventsLinksPanel } from "../features/events/components/events-links-panel";
import { useEventsModuleQuery } from "../features/events/hooks/use-events-module-query";
import type { EventsModuleViewModel } from "../features/events/model/events-module.types";

export function EventsPage() {
  const query = useEventsModuleQuery();
  const frameDescription = query.data?.pageDescription ?? "Tracking the next official windows and policy calendars.";

  if (query.isPending) {
    return (
      <ModulePageFrame
        description={frameDescription}
        lastUpdated={null}
        main={<LoadingPanelState title="Loading event windows" description="Fetching the latest official windows and calendars." />}
        side={<LoadingPanelState title="Official links loading" description="Waiting for the events payload to arrive." />}
        title="Events"
      />
    );
  }

  if (query.isError || !query.data) {
    return (
      <ModulePageFrame
        description={frameDescription}
        lastUpdated={null}
        main={
          <ErrorPanelState
            title="Events module unavailable"
            description="The events payload could not be loaded from the backend."
            action={
              <button
                className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white"
                onClick={() => {
                  void query.refetch();
                }}
                type="button"
              >
                Retry
              </button>
            }
          />
        }
        side={<LoadingPanelState title="Official links loading" description="Waiting for the events payload to arrive." />}
        title="Events"
      />
    );
  }

  const data = query.data;

  if (!data.windowSections.length) {
    return (
      <ModulePageFrame
        description={data.pageDescription}
        lastUpdated={<LastUpdatedBadge value={data.generatedAt} />}
        main={
          <EmptyPanelState
            title="No event windows yet"
            description="The backend returned an empty module payload."
            action={
              <button
                className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white"
                onClick={() => {
                  void query.refetch();
                }}
                type="button"
              >
                Retry
              </button>
            }
          />
        }
        side={<EventsLinksPanel model={data} />}
        title={data.pageTitle}
      />
    );
  }

  return (
    <ModulePageFrame
      description={data.pageDescription}
      lastUpdated={<LastUpdatedBadge value={data.generatedAt} />}
      main={<EventsOverviewContent data={data} />}
      side={<EventsLinksPanel model={data} />}
      title={data.pageTitle}
    />
  );
}

/**
 * 渲染 Events 模块的单页总览内容。
 * 参数 data 表示已经适配后的事件模块视图模型。
 * 返回全部事件窗口与空状态提示。
 */
function EventsOverviewContent({ data }: { data: EventsModuleViewModel }) {
  const sections = data.windowSections;
  const totalEvents = sections.reduce((sum, section) => sum + section.itemCount, 0);

  return (
    <section className="space-y-6">
      <header className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Timeline</p>
            <h3 className="mt-2 text-xl font-semibold text-slate-950">Major events</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">Track official calendars and market-sensitive releases in one consolidated view.</p>
          </div>
          <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
            {totalEvents} events
          </span>
        </div>
      </header>

      {sections.length ? (
        <div className="grid gap-4">
          {sections.map((section) => (
            <EventWindowCard key={section.key} section={section} />
          ))}
        </div>
      ) : (
        <article className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
          <h4 className="text-lg font-semibold text-slate-950">No events in this window</h4>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            No event matched the selected time horizon. Try switching to a longer window.
          </p>
        </article>
      )}
    </section>
  );
}
