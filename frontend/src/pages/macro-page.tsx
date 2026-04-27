import { useLocation, useSearchParams } from "react-router-dom";
import { LoadingPanelState, ErrorPanelState, EmptyPanelState } from "../shared/ui/panel-state";
import { ModulePageFrame } from "../shared/ui/module-page-frame";
import { ModuleTabBar } from "../shared/ui/module-tab-bar";
import { LastUpdatedBadge } from "../shared/ui/last-updated-badge";
import { buildModuleTabSearchParams, resolveModuleTab } from "../shared/lib/module-tabs";
import { MacroDataFactorsPanel } from "../features/macro/components/macro-data-factors-panel";
import { MacroDataModelsPanel } from "../features/macro/components/macro-data-models-panel";
import { MacroSourceMatrixPanel } from "../features/macro/components/macro-source-matrix-panel";
import { useMacroModuleQuery } from "../features/macro/hooks/use-macro-module-query";
import { MACRO_MODULE_TABS, type MacroModuleTab, type MacroModuleViewModel } from "../features/macro/model/macro-module.types";

export function MacroPage() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const query = useMacroModuleQuery();
  const activeTab = resolveModuleTab(searchParams.get("tab"), MACRO_MODULE_TABS, "data_factors");
  const toolbar = (
    <ModuleTabBar
      activeTab={activeTab}
      ariaLabel="Macro module tabs"
      pathname={location.pathname}
      searchParams={buildModuleTabSearchParams(searchParams, activeTab)}
      tabs={MACRO_MODULE_TABS}
    />
  );
  const frameDescription = query.data?.pageDescription ?? "以数据因子为核心的宏观数据工作台。";

  if (query.isPending) {
    return (
      <ModulePageFrame
        description={frameDescription}
        lastUpdated={null}
        main={
          <LoadingPanelState
            title="Loading Macro data"
            description="正在读取数据因子、数据源矩阵和模型预留信息。"
          />
        }
        side={<LoadingPanelState title="Macro side panel loading" description="等待 Macro payload 返回。" />}
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
            description="Macro 数据因子 payload 暂时无法从后端加载。"
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
        side={<LoadingPanelState title="Macro side panel loading" description="等待 Macro payload 返回。" />}
        title="Macro"
        toolbar={toolbar}
      />
    );
  }

  const data = query.data;

  if (!data.dataFactors.factors.length) {
    return (
      <ModulePageFrame
        description={data.pageDescription}
        lastUpdated={<LastUpdatedBadge value={data.generatedAt} />}
        main={
          <EmptyPanelState
            title="No macro data factors yet"
            description="后端暂未返回可展示的数据因子。"
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
        side={renderSidePanel(data)}
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
      side={renderSidePanel(data)}
      title={data.pageTitle}
      toolbar={toolbar}
    />
  );
}

/**
 * 根据当前 Macro 子标签渲染对应主内容。
 * @param activeTab URL 查询参数解析后的当前标签。
 * @param data 已适配的 Macro 模块视图模型。
 * @returns 当前标签对应的 React 内容。
 */
function renderTabContent(activeTab: MacroModuleTab, data: MacroModuleViewModel) {
  if (activeTab === "source_matrix") {
    return <MacroSourceMatrixPanel model={data} />;
  }

  if (activeTab === "data_models") {
    return <MacroDataModelsPanel model={data} />;
  }

  return <MacroDataFactorsPanel model={data} />;
}

/**
 * 渲染 Macro 页面右侧摘要，帮助快速核对数据覆盖状态。
 * @param data 已适配的 Macro 模块视图模型。
 * @returns 数据工作台状态摘要。
 */
function renderSidePanel(data: MacroModuleViewModel) {
  const summaryItems = [
    ["数据因子", data.dataFactors.factors.length],
    ["数据源矩阵", data.sourceMatrix.rows.length],
    ["降级来源", data.sourceMatrix.summary.degradedCount],
    ["预留模型", data.dataModels.models.length],
  ];

  return (
    <section className="rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Macro snapshot</p>
      <h3 className="mt-2 text-lg font-semibold text-slate-950">数据工作台状态</h3>
      <div className="mt-4 space-y-3">
        {summaryItems.map(([label, value]) => (
          <div key={String(label)} className="flex items-center justify-between gap-3 border-b border-slate-100 pb-3 last:border-b-0 last:pb-0">
            <span className="text-sm text-slate-500">{label}</span>
            <span className="text-sm font-semibold text-slate-950">{value}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
