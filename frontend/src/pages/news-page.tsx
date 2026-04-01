import { useLocation, useSearchParams } from "react-router-dom";
import { ErrorPanelState, LoadingPanelState, EmptyPanelState } from "../shared/ui/panel-state";
import { ModulePageFrame } from "../shared/ui/module-page-frame";
import { ModuleTabBar } from "../shared/ui/module-tab-bar";
import { LastUpdatedBadge } from "../shared/ui/last-updated-badge";
import { buildModuleTabSearchParams, resolveModuleTab } from "../shared/lib/module-tabs";
import { NewsChannelCard } from "../features/news/components/news-channel-card";
import { NewsFeedList } from "../features/news/components/news-feed-list";
import { NewsStatusPanel } from "../features/news/components/news-status-panel";
import { useNewsModuleQuery } from "../features/news/hooks/use-news-module-query";
import { useNewsMode } from "../shared/hooks/use-news-mode";
import { NewsModeSwitch } from "../shared/ui/news-mode-switch";
import { NEWS_MODULE_TABS, type NewsModuleTab, type NewsModuleViewModel } from "../features/news/model/news-module.types";

export function NewsPage() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const query = useNewsModuleQuery();
  const { newsMode, newsModeOptions, setNewsMode } = useNewsMode();
  const activeTab = resolveModuleTab(searchParams.get("tab"), NEWS_MODULE_TABS, "overview");
  const toolbar = (
    <div className="flex flex-col gap-3 lg:items-end">
      <ModuleTabBar
        activeTab={activeTab}
        ariaLabel="News module tabs"
        pathname={location.pathname}
        searchParams={buildModuleTabSearchParams(searchParams, activeTab)}
        tabs={NEWS_MODULE_TABS}
      />
      <NewsModeSwitch onChange={setNewsMode} options={newsModeOptions} value={newsMode} />
    </div>
  );
  const frameDescription = query.data?.pageDescription ?? "Fetching the latest channel summaries and headlines.";

  if (query.isPending) {
    return (
      <ModulePageFrame
        description={frameDescription}
        lastUpdated={null}
        main={<LoadingPanelState title="Loading news workbench" description="Fetching the latest channel summaries and headlines." />}
        side={<LoadingPanelState title="Source status loading" description="Waiting for the news payload to arrive." />}
        title="News"
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
            title="News module unavailable"
            description="The news module could not be loaded from the backend."
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
        side={<LoadingPanelState title="Source status loading" description="Waiting for the news payload to arrive." />}
        title="News"
        toolbar={toolbar}
      />
    );
  }

  const data = query.data;

  if (!data.channelSummaries.length) {
    return (
      <ModulePageFrame
        description={data.pageDescription}
        lastUpdated={<LastUpdatedBadge value={data.generatedAt} />}
        main={
          <EmptyPanelState
            title="No news channels yet"
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
        side={<NewsStatusPanel model={data} />}
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
      side={<NewsStatusPanel model={data} />}
      title={data.pageTitle}
      toolbar={toolbar}
    />
  );
}

function renderTabContent(activeTab: NewsModuleTab, data: NewsModuleViewModel) {
  if (activeTab === "channels") {
    return (
      <section className="space-y-6 rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Channels</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-950">Channel summaries</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">{data.moduleNote}</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {data.channelSummaries.map((channel) => (
            <NewsChannelCard key={channel.id} channel={channel} />
          ))}
        </div>
      </section>
    );
  }

  if (activeTab === "sources") {
    return (
      <section className="space-y-6 rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Sources</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-950">Source coverage</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            The upstream status and mode configuration are summarized in the side panel.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {data.newsModeOptions.map((option) => (
            <article key={option.value} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Mode</p>
              <h4 className="mt-2 text-base font-semibold text-slate-950">{option.label}</h4>
              <p className="mt-2 text-sm text-slate-600">{option.value === data.newsMode ? "Active news pipeline" : "Available source mode"}</p>
            </article>
          ))}
        </div>
      </section>
    );
  }

  if (activeTab === "brief") {
    return (
      <section className="space-y-6 rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Brief</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-950">Working summary</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">{data.moduleNote}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
          <p className="text-sm font-medium text-slate-500">Latest top line</p>
          <p className="mt-2 text-base leading-7 text-slate-700">{data.rankedHeadlines[0]?.summary || data.pageDescription}</p>
          <p className="mt-4 text-sm text-slate-500">{data.channelSummaries.length} channels, {data.rankedHeadlines.length} ranked headlines.</p>
        </div>
      </section>
    );
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Overview</p>
            <h3 className="mt-2 text-xl font-semibold text-slate-950">Channel summaries</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">{data.moduleNote}</p>
          </div>
          <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
            {data.channelSummaries.length} channels
          </span>
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          {data.channelSummaries.map((channel) => (
            <NewsChannelCard key={channel.id} channel={channel} />
          ))}
        </div>
      </section>

      <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Overview</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-950">Ranked headlines</h3>
        </div>
        <div className="mt-5">
          <NewsFeedList headlines={data.rankedHeadlines.slice(0, 6)} />
        </div>
      </section>
    </div>
  );
}
