import { LastUpdatedBadge } from "../../../shared/ui/last-updated-badge";
import type { EventsModuleTab, EventsModuleViewModel } from "../model/events-module.types";

type EventsLinksPanelProps = {
  model: EventsModuleViewModel;
  activeTab: EventsModuleTab;
};

const tabCopy: Record<EventsModuleTab, string> = {
  timeline: "Timeline mode keeps the next windows stacked in order of urgency.",
  calendar: "Calendar mode keeps the date cadence in view for the next official releases.",
  watch: "Watch mode highlights the most actionable items and their likely market impact.",
  sources: "Sources mode collects the official calendars and coverage links in one place.",
};

export function EventsLinksPanel({ model, activeTab }: EventsLinksPanelProps) {
  return (
    <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Official links and watch panel</p>
      <h3 className="mt-3 text-lg font-semibold text-slate-950">Operational snapshot</h3>
      <p className="mt-3 text-sm leading-6 text-slate-600">{tabCopy[activeTab]}</p>

      <div className="mt-5 space-y-3">
        <StatusRow label="Windows" value={`${model.windowSections.length}`} />
        <StatusRow label="Events" value={`${model.totalItems}`} />
        <StatusRow label="Official links" value={`${model.officialLinks.length}`} />
        <StatusRow label="Module state" value={model.moduleStatus} />
      </div>

      <div className="mt-5">
        <LastUpdatedBadge value={model.generatedAt} />
      </div>

      <div className="mt-6 space-y-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Official links</p>
          <div className="mt-3 space-y-2">
            {model.officialLinks.length ? (
              model.officialLinks.map((link) => (
                <a
                  key={`${link.region}-${link.label}-${link.url}`}
                  className="flex items-start justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700 transition hover:border-slate-300 hover:text-slate-950"
                  href={link.url}
                >
                  <span>{link.label}</span>
                  <span className="text-xs text-slate-500">{link.region}</span>
                </a>
              ))
            ) : (
              <p className="text-sm text-slate-500">No official links were returned.</p>
            )}
          </div>
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Watch items</p>
          <div className="mt-3 space-y-2">
            {model.watchItems.length ? (
              model.watchItems.map((item) => (
                <div key={`${item.windowKey}-${item.title}-${item.expectedDate}`} className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-slate-950">{item.title}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        {item.region} | {item.windowTitle}
                      </p>
                    </div>
                    <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">{item.confidence}</span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-600">{item.impactSummary}</p>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">No watch items were returned.</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function StatusRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-100 pb-3 last:border-b-0 last:pb-0">
      <span className="text-sm text-slate-500">{label}</span>
      <span className="text-sm font-medium text-slate-950">{value}</span>
    </div>
  );
}
