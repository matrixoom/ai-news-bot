import { LastUpdatedBadge } from "../../../shared/ui/last-updated-badge";
import type { MarketModuleViewModel } from "../model/market-module.types";

type MarketWatchPanelProps = {
  model: MarketModuleViewModel;
};

/**
 * 渲染 Market 单页右侧观察面板。
 * 参数 model 表示市场模块视图模型。
 * 返回市场状态摘要、观察清单与更新时间。
 */
export function MarketWatchPanel({ model }: MarketWatchPanelProps) {
  return (
    <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Watch status</p>
      <h3 className="mt-3 text-lg font-semibold text-slate-950">Watchlist</h3>
      <p className="mt-3 text-sm leading-6 text-slate-600">Overview keeps the market model set compact and easy to scan.</p>

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
