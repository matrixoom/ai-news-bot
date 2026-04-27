import { LastUpdatedBadge } from "../../../shared/ui/last-updated-badge";
import type { MacroModuleTab, MacroModuleViewModel } from "../model/macro-module.types";

type MacroSourcesPanelProps = {
  model: MacroModuleViewModel;
  activeTab: MacroModuleTab;
};

const tabCopy: Record<MacroModuleTab, string> = {
  overview: "The overview keeps the comparison set compact and readable.",
  compare: "Compare mode emphasizes the delta and source links for each pair.",
  indicators: "Indicator mode surfaces the underlying readings and their latest values.",
  sources: "Source mode collects the unique source registry across the module.",
};

export function MacroSourcesPanel({ model, activeTab }: MacroSourcesPanelProps) {
  return (
    <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Source and indicator panel</p>
      <h3 className="mt-3 text-lg font-semibold text-slate-950">Operational snapshot</h3>
      <p className="mt-3 text-sm leading-6 text-slate-600">{tabCopy[activeTab]}</p>

      <div className="mt-5 space-y-3">
        <StatusRow label="Comparisons" value={`${model.comparisonSections.length}`} />
        <StatusRow label="Indicators" value={`${model.indicators.length}`} />
        <StatusRow label="Sources" value={`${model.sources.length}`} />
        <StatusRow label="Module state" value={model.moduleStatus} />
      </div>

      <div className="mt-5">
        <LastUpdatedBadge value={model.generatedAt} />
      </div>

      <div className="mt-6 space-y-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Sources</p>
          <div className="mt-3 space-y-2">
            {model.sources.length ? (
              model.sources.map((source) => (
                <a
                  key={`${source.label}-${source.url}`}
                  className="flex items-start justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700 transition hover:border-slate-300 hover:text-slate-950"
                  href={source.url}
                >
                  <span>{source.label}</span>
                  <span className="text-xs text-slate-500">{source.sectionTitles.length} pairs</span>
                </a>
              ))
            ) : (
              <p className="text-sm text-slate-500">No source links were returned.</p>
            )}
          </div>
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Indicators</p>
          <div className="mt-3 space-y-2">
            {model.indicators.slice(0, 4).map((indicator) => (
              <div key={indicator.key} className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-slate-950">{indicator.label}</p>
                    <p className="mt-1 text-xs text-slate-500">{indicator.frequency}</p>
                  </div>
                  <span className="text-sm font-semibold text-slate-950">{indicator.latestValue}</span>
                </div>
              </div>
            ))}
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
