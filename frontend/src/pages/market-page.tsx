import { ErrorPanelState, LoadingPanelState, EmptyPanelState } from "../shared/ui/panel-state";
import { ModulePageFrame } from "../shared/ui/module-page-frame";
import { LastUpdatedBadge } from "../shared/ui/last-updated-badge";
import { MarketSignalCard } from "../features/market/components/market-signal-card";
import { MarketWatchPanel } from "../features/market/components/market-watch-panel";
import { useMarketModuleQuery } from "../features/market/hooks/use-market-module-query";
import type { MarketModuleViewModel } from "../features/market/model/market-module.types";

export function MarketPage() {
  const query = useMarketModuleQuery();
  const frameDescription = query.data?.pageDescription ?? "Tracking the latest index models and watch summaries.";

  if (query.isPending) {
    return (
      <ModulePageFrame
        description={frameDescription}
        lastUpdated={null}
        main={
          <LoadingPanelState
            title="Loading market models"
            description="Fetching the latest signal cards and watch summaries."
          />
        }
        side={<LoadingPanelState title="Watch panel loading" description="Waiting for the market payload to arrive." />}
        title="Market"
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
            title="Market module unavailable"
            description="The market signal payload could not be loaded from the backend."
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
        side={<LoadingPanelState title="Watch panel loading" description="Waiting for the market payload to arrive." />}
        title="Market"
      />
    );
  }

  const data = query.data;

  if (!data.signalCards.length) {
    return (
      <ModulePageFrame
        description={data.pageDescription}
        lastUpdated={<LastUpdatedBadge value={data.generatedAt} />}
        main={
          <EmptyPanelState
            title="No market signals yet"
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
        side={<MarketWatchPanel model={data} />}
        title={data.pageTitle}
      />
    );
  }

  return (
    <ModulePageFrame
      description={data.pageDescription}
      lastUpdated={<LastUpdatedBadge value={data.generatedAt} />}
      main={<MarketOverviewContent data={data} />}
      side={<MarketWatchPanel model={data} />}
      title={data.pageTitle}
    />
  );
}

/**
 * 渲染 Market 模块的单页总览内容。
 * 参数 data 表示已经适配后的市场模块视图模型。
 * 返回市场信号卡片与当前姿态摘要。
 */
function MarketOverviewContent({ data }: { data: MarketModuleViewModel }) {
  return (
    <section className="space-y-6">
      <header className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Overview</p>
            <h3 className="mt-2 text-xl font-semibold text-slate-950">Market overview</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">{data.moduleNote}</p>
          </div>
          <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
            {data.signalCards.length} models
          </span>
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        {data.signalCards.slice(0, 2).map((card) => (
          <MarketSignalCard key={card.key} card={card} />
        ))}
      </div>

      <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Watch summary</p>
        <h3 className="mt-2 text-xl font-semibold text-slate-950">Current posture</h3>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          The overview keeps the strongest signal cards in front while the side panel tracks the full watch list.
        </p>
      </section>
    </section>
  );
}
