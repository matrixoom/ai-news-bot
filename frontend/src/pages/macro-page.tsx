import { useLocation, useSearchParams } from "react-router-dom";
import { LoadingPanelState, ErrorPanelState, EmptyPanelState } from "../shared/ui/panel-state";
import { ModulePageFrame } from "../shared/ui/module-page-frame";
import { ModuleTabBar } from "../shared/ui/module-tab-bar";
import { LastUpdatedBadge } from "../shared/ui/last-updated-badge";
import { buildModuleTabSearchParams, resolveModuleTab } from "../shared/lib/module-tabs";
import { MacroComparisonCard } from "../features/macro/components/macro-comparison-card";
import { MacroSourcesPanel } from "../features/macro/components/macro-sources-panel";
import { useMacroModuleQuery } from "../features/macro/hooks/use-macro-module-query";
import { MACRO_MODULE_TABS, type MacroModuleTab, type MacroModuleViewModel } from "../features/macro/model/macro-module.types";

export function MacroPage() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const query = useMacroModuleQuery();
  const activeTab = resolveModuleTab(searchParams.get("tab"), MACRO_MODULE_TABS, "overview");
  const toolbar = (
    <ModuleTabBar
      activeTab={activeTab}
      ariaLabel="Macro module tabs"
      pathname={location.pathname}
      searchParams={buildModuleTabSearchParams(searchParams, activeTab)}
      tabs={MACRO_MODULE_TABS}
    />
  );
  const frameDescription = query.data?.pageDescription ?? "Comparing official macro indicators side by side.";

  if (query.isPending) {
    return (
      <ModulePageFrame
        description={frameDescription}
        lastUpdated={null}
        main={
          <LoadingPanelState
            title="Loading macro comparisons"
            description="Fetching the latest indicator pairs and source links."
          />
        }
        side={<LoadingPanelState title="Source panel loading" description="Waiting for the macro payload to arrive." />}
        title="Macro"
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
            title="Macro module unavailable"
            description="The comparison payload could not be loaded from the backend."
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
        side={<LoadingPanelState title="Source panel loading" description="Waiting for the macro payload to arrive." />}
        title="Macro"
        toolbar={toolbar}
      />
    );
  }

  const data = query.data;

  if (!data.comparisonSections.length) {
    return (
      <ModulePageFrame
        description={data.pageDescription}
        lastUpdated={<LastUpdatedBadge value={data.generatedAt} />}
        main={
          <EmptyPanelState
            title="No macro comparisons yet"
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
        side={<MacroSourcesPanel activeTab={activeTab} model={data} />}
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
      side={<MacroSourcesPanel activeTab={activeTab} model={data} />}
      title={data.pageTitle}
      toolbar={toolbar}
    />
  );
}

function renderTabContent(activeTab: MacroModuleTab, data: MacroModuleViewModel) {
  if (activeTab === "compare") {
    return (
      <section className="space-y-4">
        <header className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Compare</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-950">Side-by-side comparisons</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">{data.moduleNote}</p>
        </header>
        <div className="space-y-4">
          {data.comparisonSections.map((section) => (
            <MacroComparisonCard key={section.key} section={section} />
          ))}
        </div>
      </section>
    );
  }

  if (activeTab === "indicators") {
    return (
      <section className="space-y-4">
        <header className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Indicators</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-950">Indicator snapshots</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">The current readings are organized around each comparison pair.</p>
        </header>
        <div className="grid gap-4 md:grid-cols-2">
          {data.comparisonSections.map((section) => (
            <article key={section.key} className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">{section.title}</p>
              <div className="mt-4 grid gap-3">
                <IndicatorLine indicator={section.primary} />
                {section.secondary ? <IndicatorLine indicator={section.secondary} /> : null}
              </div>
            </article>
          ))}
        </div>
      </section>
    );
  }

  if (activeTab === "sources") {
    return (
      <section className="space-y-4">
        <header className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Sources</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-950">Source register</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">Official sources are grouped by comparison pair for quick review.</p>
        </header>
        <div className="space-y-4">
          {data.comparisonSections.map((section) => (
            <article key={section.key} className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="max-w-2xl">
                  <h4 className="text-lg font-semibold text-slate-950">{section.title}</h4>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{section.summary}</p>
                </div>
                <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
                  {section.deltaLabel}
                </span>
              </div>
              <div className="mt-5 flex flex-wrap gap-2">
                {section.sources.map((source) => (
                  <a
                    key={`${source.label}-${source.url}`}
                    className="inline-flex rounded-full border border-slate-200 bg-white px-3 py-1 text-sm font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-950"
                    href={source.url}
                  >
                    {source.label}
                  </a>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <header className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Overview</p>
            <h3 className="mt-2 text-xl font-semibold text-slate-950">Macro overview</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">{data.moduleNote}</p>
          </div>
          <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
            {data.comparisonSections.length} pairs
          </span>
        </div>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        {data.comparisonSections.slice(0, 2).map((section) => (
          <MacroComparisonCard key={section.key} section={section} />
        ))}
      </div>
    </section>
  );
}

function IndicatorLine({ indicator }: { indicator: MacroModuleViewModel["indicators"][number] }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-slate-950">{indicator.label}</p>
          <p className="mt-1 text-xs uppercase tracking-[0.16em] text-slate-500">{indicator.frequency}</p>
        </div>
        <div className="text-right">
          <p className="text-sm font-semibold text-slate-950">{indicator.latestValue}</p>
          <p className="mt-1 text-xs text-slate-500">{indicator.changeLabel}</p>
        </div>
      </div>
    </div>
  );
}
