import { useLocation, useSearchParams } from "react-router-dom";
import { ErrorPanelState, LoadingPanelState, EmptyPanelState } from "../shared/ui/panel-state";
import { ModulePageFrame } from "../shared/ui/module-page-frame";
import { ModuleTabBar } from "../shared/ui/module-tab-bar";
import { LastUpdatedBadge } from "../shared/ui/last-updated-badge";
import { buildModuleTabSearchParams, resolveModuleTab } from "../shared/lib/module-tabs";
import { EventWindowCard } from "../features/events/components/event-window-card";
import { EventsLinksPanel } from "../features/events/components/events-links-panel";
import { useEventsModuleQuery } from "../features/events/hooks/use-events-module-query";
import {
  EVENTS_MODULE_TABS,
  type EventsModuleTab,
  type EventsModuleViewModel,
} from "../features/events/model/events-module.types";

export function EventsPage() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const query = useEventsModuleQuery();
  const activeTab = resolveModuleTab(searchParams.get("tab"), EVENTS_MODULE_TABS, "timeline");
  const toolbar = (
    <ModuleTabBar
      activeTab={activeTab}
      ariaLabel="Events module tabs"
      pathname={location.pathname}
      searchParams={buildModuleTabSearchParams(searchParams, activeTab)}
      tabs={EVENTS_MODULE_TABS}
    />
  );
  const frameDescription = query.data?.pageDescription ?? "Tracking the next official windows and policy calendars.";

  if (query.isPending) {
    return (
      <ModulePageFrame
        description={frameDescription}
        lastUpdated={null}
        main={<LoadingPanelState title="Loading event windows" description="Fetching the latest official windows and calendars." />}
        side={<LoadingPanelState title="Official links loading" description="Waiting for the events payload to arrive." />}
        title="Events"
        toolbar={toolbar}
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
        toolbar={toolbar}
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
        side={<EventsLinksPanel activeTab={activeTab} model={data} />}
        title={data.pageTitle}
        toolbar={toolbar}
      />
    );
  }

  return (
    <ModulePageFrame
      description={data.pageDescription}
      lastUpdated={<LastUpdatedBadge value={data.generatedAt} />}
      main={renderTabContent(activeTab, data)}
      side={<EventsLinksPanel activeTab={activeTab} model={data} />}
      title={data.pageTitle}
      toolbar={toolbar}
    />
  );
}

function renderTabContent(activeTab: EventsModuleTab, data: EventsModuleViewModel) {
  if (activeTab === "calendar") {
    return (
      <section className="space-y-6">
        <header className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Calendar</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-950">Official calendar view</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">{data.moduleNote}</p>
        </header>

        <div className="grid gap-4 md:grid-cols-3">
          {data.watchItems.slice(0, 3).map((item) => (
            <article key={`${item.windowKey}-${item.title}-${item.expectedDate}`} className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{item.windowTitle}</p>
              <h4 className="mt-2 text-base font-semibold text-slate-950">{item.title}</h4>
              <p className="mt-2 text-sm leading-6 text-slate-600">{item.impactSummary}</p>
              <p className="mt-4 text-sm text-slate-500">
                {item.region} | {item.expectedDate}
              </p>
            </article>
          ))}
        </div>

        <div className="grid gap-4">
          {data.windowSections.map((section) => (
            <EventWindowCard key={section.key} section={section} />
          ))}
        </div>
      </section>
    );
  }

  if (activeTab === "watch") {
    return (
      <section className="space-y-6">
        <header className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Watch</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-950">Watch list</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">The watch list pulls the most immediate items forward for quick review.</p>
        </header>

        <div className="grid gap-4 md:grid-cols-2">
          {data.watchItems.map((item) => (
            <article key={`${item.windowKey}-${item.title}-${item.expectedDate}`} className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{item.windowTitle}</p>
              <h4 className="mt-2 text-lg font-semibold text-slate-950">{item.title}</h4>
              <p className="mt-2 text-sm leading-6 text-slate-600">{item.impactSummary}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600">{item.region}</span>
                <span className="inline-flex rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600">{item.expectedDate}</span>
                <span className="inline-flex rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600">{item.timeWindow}</span>
              </div>
            </article>
          ))}
        </div>
      </section>
    );
  }

  if (activeTab === "sources") {
    return (
      <section className="space-y-6">
        <header className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Sources</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-950">Official source registry</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">The registry keeps the agency calendars and institutional source links together.</p>
        </header>

        <div className="grid gap-4">
          {data.officialLinks.map((link) => (
            <a
              key={`${link.region}-${link.label}-${link.url}`}
              className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm transition hover:border-slate-300"
              href={link.url}
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{link.region}</p>
                  <h4 className="mt-2 text-lg font-semibold text-slate-950">{link.label}</h4>
                </div>
                <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
                  Official
                </span>
              </div>
              <p className="mt-4 text-sm text-slate-600 break-all">{link.url}</p>
            </a>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <header className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Timeline</p>
            <h3 className="mt-2 text-xl font-semibold text-slate-950">Upcoming windows</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">{data.moduleNote}</p>
          </div>
          <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
            {data.windowSections.length} windows
          </span>
        </div>
      </header>

      <div className="grid gap-4">
        {data.windowSections.map((section) => (
          <EventWindowCard key={section.key} section={section} />
        ))}
      </div>
    </section>
  );
}
