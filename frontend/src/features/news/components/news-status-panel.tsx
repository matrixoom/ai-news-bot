import { LastUpdatedBadge } from "../../../shared/ui/last-updated-badge";
import type { NewsModuleViewModel } from "../model/news-module.types";

type NewsStatusPanelProps = {
  model: NewsModuleViewModel;
};

export function NewsStatusPanel({ model }: NewsStatusPanelProps) {
  return (
    <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Source status</p>
      <h3 className="mt-3 text-lg font-semibold text-slate-950">Operational snapshot</h3>
      <p className="mt-3 text-sm leading-6 text-slate-600">{model.pageDescription}</p>

      <div className="mt-5 space-y-3">
        <StatusRow label="News mode" value={model.newsModeLabel} />
        <StatusRow label="Upstream" value={model.upstreamServiceStatus} />
        <StatusRow label="Module state" value={model.moduleStatus} />
        <StatusRow label="Channels" value={`${model.channelSummaries.length}`} />
        <StatusRow label="Headlines" value={`${model.rankedHeadlines.length}`} />
      </div>

      <div className="mt-5">
        <LastUpdatedBadge value={model.generatedAt} />
      </div>

      <div className="mt-5 space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Mode options</p>
        <div className="flex flex-wrap gap-2">
          {model.newsModeOptions.map((option) => (
            <span
              key={option.value}
              className={[
                "rounded-full border px-3 py-1 text-xs font-medium",
                option.value === model.newsMode ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200 bg-slate-50 text-slate-600",
              ].join(" ")}
            >
              {option.label}
            </span>
          ))}
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
