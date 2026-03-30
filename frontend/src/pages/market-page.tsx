import { useLocation, useSearchParams } from "react-router-dom";
import { ErrorPanelState, LoadingPanelState, EmptyPanelState } from "../shared/ui/panel-state";
import { ModulePageFrame } from "../shared/ui/module-page-frame";
import { ModuleTabBar } from "../shared/ui/module-tab-bar";
import { LastUpdatedBadge } from "../shared/ui/last-updated-badge";
import { buildModuleTabSearchParams, resolveModuleTab } from "../shared/lib/module-tabs";
import { MarketSignalCard } from "../features/market/components/market-signal-card";
import { MarketWatchPanel } from "../features/market/components/market-watch-panel";
import { useMarketModuleQuery } from "../features/market/hooks/use-market-module-query";
import {
  MARKET_MODULE_TABS,
  type MarketModuleTab,
  type MarketModuleViewModel,
} from "../features/market/model/market-module.types";

export function MarketPage() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const query = useMarketModuleQuery();
  const activeTab = resolveModuleTab(searchParams.get("tab"), MARKET_MODULE_TABS, "overview");
  const toolbar = (
    <ModuleTabBar
      activeTab={activeTab}
      ariaLabel="Market module tabs"
      pathname={location.pathname}
      searchParams={buildModuleTabSearchParams(searchParams, activeTab)}
      tabs={MARKET_MODULE_TABS}
    />
  );
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
        toolbar={toolbar}
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
        side={<MarketWatchPanel activeTab={activeTab} model={data} />}
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
      side={<MarketWatchPanel activeTab={activeTab} model={data} />}
      title={data.pageTitle}
      toolbar={toolbar}
    />
  );
}

function renderTabContent(activeTab: MarketModuleTab, data: MarketModuleViewModel) {
  if (activeTab === "signals") {
    return (
      <section className="space-y-6 rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Signals</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-950">Signal matrix</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">{data.moduleNote}</p>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          {data.signalCards.map((card) => (
            <MarketSignalCard key={card.key} card={card} />
          ))}
        </div>
      </section>
    );
  }

  if (activeTab === "models") {
    return (
      <section className="space-y-6 rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Models</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-950">Model table</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">Each card keeps the latest close, moving average, and source in view.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {data.signalCards.map((card) => (
            <MarketSignalCard key={card.key} card={card} compact />
          ))}
        </div>
      </section>
    );
  }

  if (activeTab === "watchlist") {
    return (
      <section className="space-y-6 rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Watchlist</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-950">Focus list</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">The strongest signal names are grouped here for quick follow-up.</p>
        </div>
        <div className="grid gap-4">
          {data.signalCards.slice(0, 4).map((card) => (
            <article key={card.key} className="rounded-[1.75rem] border border-slate-200 bg-slate-50 p-5 shadow-sm">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h4 className="text-lg font-semibold text-slate-950">{card.label}</h4>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{card.explanation}</p>
                </div>
                <span className="inline-flex rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-slate-600">
                  {card.signal}
                </span>
              </div>
              <p className="mt-4 text-sm text-slate-500">{card.sourceLabel}</p>
            </article>
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
