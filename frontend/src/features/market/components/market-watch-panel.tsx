import { LastUpdatedBadge } from "../../../shared/ui/last-updated-badge";
import type { MarketModuleTab, MarketModuleViewModel } from "../model/market-module.types";

type MarketWatchPanelProps = {
  model: MarketModuleViewModel;
  activeTab: MarketModuleTab;
};

const tabCopy: Record<MarketModuleTab, string> = {
  overview: "Overview keeps the market model set compact and easy to scan.",
  signals: "Signals mode emphasizes the live posture of each tracked index.",
  models: "Models mode surfaces the data window and source behind each card.",
  watchlist: "Watchlist mode keeps the most actionable signals at the top.",
};

export function MarketWatchPanel({ model, activeTab }: MarketWatchPanelProps) {
  return (
    <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Watch status</p>
      <h3 className="mt-3 text-lg font-semibold text-slate-950">Watchlist</h3>
      <p className="mt-3 text-sm leading-6 text-slate-600">{tabCopy[activeTab]}</p>

      <div className="mt-5 space-y-3">
        {model.watchSummaries.map((summary) => (
          <SummaryCard key={summary.label} summary={summary} />
        ))}
      </div>

      <div className="mt-6 space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Latest watch items</p>
        <div className="space-y-2">
          {model.watchItems.map((item) => (
            <div key={item.key} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-slate-950">{item.label}</p>
                  <p className="mt-1 text-xs text-slate-500">{item.sourceLabel}</p>
                </div>
                <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-600">
                  {item.signal}
                </span>
              </div>
              <p className="mt-3 text-sm text-slate-600">{item.tradeDate}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-6">
        <LastUpdatedBadge value={model.generatedAt} />
      </div>
    </section>
  );
}

function SummaryCard({ summary }: { summary: MarketModuleViewModel["watchSummaries"][number] }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{summary.label}</p>
      <p className="mt-2 text-sm font-semibold text-slate-950">{summary.value}</p>
      <p className="mt-1 text-sm leading-6 text-slate-600">{summary.detail}</p>
    </div>
  );
}
