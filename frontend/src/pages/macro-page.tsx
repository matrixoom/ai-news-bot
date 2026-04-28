import { LoadingPanelState, ErrorPanelState, EmptyPanelState } from "../shared/ui/panel-state";
import { ModulePageFrame } from "../shared/ui/module-page-frame";
import { LastUpdatedBadge } from "../shared/ui/last-updated-badge";
import { useMacroModuleQuery } from "../features/macro/hooks/use-macro-module-query";
import type { MacroCardView, MacroModuleViewModel } from "../features/macro/model/macro-module.types";

export function MacroPage() {
  const query = useMacroModuleQuery();
  const frameDescription = query.data?.pageDescription ?? "Tracking macro indicators and paired comparisons.";

  if (query.isPending) {
    return (
      <ModulePageFrame
        description={frameDescription}
        lastUpdated={null}
        main={<LoadingPanelState title="Loading Macro data" description="Fetching the latest macro indicators." />}
        side={<LoadingPanelState title="Macro side panel loading" description="Waiting for the dashboard payload." />}
        title="Macro"
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
            description="Macro data could not be loaded from the dashboard payload."
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
        side={<LoadingPanelState title="Macro side panel loading" description="Waiting for the dashboard payload." />}
        title="Macro"
      />
    );
  }

  const data = query.data;

  if (!data.macroCards.length) {
    return (
      <ModulePageFrame
        description={data.pageDescription}
        lastUpdated={<LastUpdatedBadge value={data.generatedAt} />}
        main={
          <EmptyPanelState
            title="No macro indicators yet"
            description="The dashboard payload returned an empty macro section."
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
        side={<MacroStatusPanel model={data} />}
        title={data.pageTitle}
      />
    );
  }

  return (
    <ModulePageFrame
      description={data.pageDescription}
      lastUpdated={<LastUpdatedBadge value={data.generatedAt} />}
      main={<MacroOverviewContent model={data} />}
      side={<MacroStatusPanel model={data} />}
      title={data.pageTitle}
    />
  );
}

/**
 * 渲染 Macro 单页总览主体。
 * @param model 已适配的 Macro 聚合视图模型。
 * @returns 宏观指标卡片列表。
 */
function MacroOverviewContent({ model }: { model: MacroModuleViewModel }) {
  return (
    <section className="space-y-6">
      <header className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Overview</p>
            <h3 className="mt-2 text-xl font-semibold text-slate-950">Macro overview</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Macro now uses one consolidated page backed by the shared dashboard payload.
            </p>
          </div>
          <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
            {model.macroCards.length} cards
          </span>
        </div>
      </header>

      <div className="grid gap-4 xl:grid-cols-2">
        {model.macroCards.map((card) => (
          <MacroCard key={card.key} card={card} />
        ))}
      </div>
    </section>
  );
}

/**
 * 渲染单张宏观指标卡片。
 * @param card 单张 Macro 卡片视图模型。
 * @returns 指标摘要、主副指标与来源信息。
 */
function MacroCard({ card }: { card: MacroCardView }) {
  return (
    <article className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{card.status}</p>
          <h4 className="mt-2 text-lg font-semibold text-slate-950">{card.title}</h4>
          <p className="mt-2 text-sm leading-6 text-slate-600">{card.description}</p>
        </div>
      </div>

      <p className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-700">
        {card.summary}
      </p>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <IndicatorBlock label="Primary" indicator={card.primary} />
        {card.secondary ? <IndicatorBlock label="Secondary" indicator={card.secondary} /> : null}
      </div>

      {card.sourceLabels.length ? (
        <p className="mt-4 text-xs text-slate-500">Sources: {card.sourceLabels.join(", ")}</p>
      ) : null}
    </article>
  );
}

/**
 * 渲染单个指标读数块。
 * @param label 指标角色标签。
 * @param indicator 单个指标视图模型。
 * @returns 指标读数与上下文。
 */
function IndicatorBlock({ label, indicator }: { label: string; indicator: MacroCardView["primary"] }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <h5 className="mt-2 text-base font-semibold text-slate-950">{indicator.label}</h5>
      <p className="mt-2 text-2xl font-semibold text-slate-950">{indicator.latestValue}</p>
      <p className="mt-1 text-sm text-slate-600">{indicator.changeLabel || indicator.periodLabel}</p>
      <p className="mt-3 text-sm leading-6 text-slate-600">{indicator.context}</p>
      <p className="mt-3 text-xs text-slate-500">{indicator.sourceLabel}</p>
    </div>
  );
}

/**
 * 渲染 Macro 单页右侧状态面板。
 * @param model 已适配的 Macro 聚合视图模型。
 * @returns 宏观模块状态摘要。
 */
function MacroStatusPanel({ model }: { model: MacroModuleViewModel }) {
  return (
    <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Macro snapshot</p>
      <h3 className="mt-3 text-lg font-semibold text-slate-950">Operational status</h3>
      <p className="mt-3 text-sm leading-6 text-slate-600">
        Macro 子页已移除，当前仅保留聚合指标总览。
      </p>
      <div className="mt-5 space-y-3">
        {model.statusSummaries.map((summary) => (
          <div key={summary.label} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{summary.label}</p>
            <p className="mt-2 text-sm font-semibold text-slate-950">{summary.value}</p>
            <p className="mt-1 text-sm leading-6 text-slate-600">{summary.detail}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
