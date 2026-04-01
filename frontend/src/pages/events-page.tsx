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
  const activeTab = resolveModuleTab(searchParams.get("tab"), EVENTS_MODULE_TABS, "week");
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
  const tabMeta = TAB_META[activeTab];
  const sections = filterSectionsByTab(data, activeTab);
  const totalEvents = sections.reduce((sum, section) => sum + section.itemCount, 0);

  return (
    <section className="space-y-6">
      <header className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">{tabMeta.eyebrow}</p>
            <h3 className="mt-2 text-xl font-semibold text-slate-950">{tabMeta.title}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">{tabMeta.description}</p>
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

const HORIZON_DAYS: Record<EventsModuleTab, number> = {
  week: 7,
  month: 30,
  halfyear: 180,
};

const TAB_META: Record<EventsModuleTab, { eyebrow: string; title: string; description: string }> = {
  week: {
    eyebrow: "近一周",
    title: "One-week major events",
    description: "Focus on the next 7 days to keep the short-horizon catalysts in view.",
  },
  month: {
    eyebrow: "近1个月",
    title: "One-month major events",
    description: "Track the next 30 days for planning and cross-module scenario prep.",
  },
  halfyear: {
    eyebrow: "近6个月",
    title: "Six-month major events",
    description: "Keep medium-term policy and macro catalysts visible for allocation reviews.",
  },
};

function filterSectionsByTab(data: EventsModuleViewModel, activeTab: EventsModuleTab) {
  const horizonDays = HORIZON_DAYS[activeTab];
  const anchorDate = resolveAnchorDate(data.generatedAt);

  return data.windowSections
    .map((section) => {
      const items = section.items.filter((item) => isDateWithinHorizon(item.expectedDate, anchorDate, horizonDays));

      return {
        ...section,
        itemCount: items.length,
        items,
      };
    })
    .filter((section) => section.items.length > 0);
}

function resolveAnchorDate(generatedAt: string): Date {
  const timestamp = Date.parse(generatedAt);

  if (Number.isNaN(timestamp)) {
    return new Date();
  }

  return new Date(timestamp);
}

function isDateWithinHorizon(expectedDate: string, anchorDate: Date, horizonDays: number): boolean {
  const target = Date.parse(expectedDate);

  if (Number.isNaN(target)) {
    return false;
  }

  const start = new Date(anchorDate);
  start.setHours(0, 0, 0, 0);

  const end = new Date(target);
  end.setHours(0, 0, 0, 0);

  const diffInDays = (end.getTime() - start.getTime()) / (24 * 60 * 60 * 1000);
  return diffInDays >= 0 && diffInDays <= horizonDays;
}
