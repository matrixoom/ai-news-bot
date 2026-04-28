import type { MacroIndicatorRaw, MacroModuleRawPayload, MacroModuleViewModel } from "./macro-module.types";

/**
 * 将 Dashboard 聚合 payload 中的 Macro 数据转换为单页视图模型。
 * @param response 后端 `/api/frontend/dashboard` 返回的聚合 JSON。
 * @returns Macro 页面组件消费的总览视图模型。
 */
export function adaptMacroModule(response: MacroModuleRawPayload): MacroModuleViewModel {
  const macroCards = response.macro_sections.map((section) => ({
    key: section.key,
    title: section.title,
    status: section.status,
    description: section.description,
    summary: section.summary,
    primary: adaptIndicator(section.primary),
    secondary: section.secondary ? adaptIndicator(section.secondary) : null,
    sourceLabels: section.sources.map((source) => source.label).filter(Boolean),
  }));

  const degradedCount = macroCards.filter((card) => card.status === "degraded").length;
  const liveCount = macroCards.filter((card) => card.status === "live").length;

  return {
    generatedAt: response.generated_at,
    pageTitle: "Macro",
    pageDescription: "Macro indicators and paired comparisons from the shared dashboard payload.",
    moduleStatus: degradedCount ? "degraded" : liveCount ? "live" : (macroCards[0]?.status ?? "compatible"),
    macroCards,
    statusSummaries: [
      {
        label: "Macro cards",
        value: `${macroCards.length}`,
        detail: "从 /api/frontend/dashboard 的 macro_sections 聚合渲染。",
      },
      {
        label: "Live cards",
        value: `${liveCount}`,
        detail: "当前可用的实时或兼容宏观指标卡片。",
      },
      {
        label: "Degraded cards",
        value: `${degradedCount}`,
        detail: "存在数据源降级或缺口的宏观指标卡片。",
      },
    ],
  };
}

/**
 * 转换单个宏观指标读数。
 * @param indicator 后端返回的蛇形命名指标字段。
 * @returns 前端展示所需的驼峰命名指标字段。
 */
function adaptIndicator(indicator: MacroIndicatorRaw) {
  return {
    key: indicator.key,
    label: indicator.label,
    latestValue: indicator.latest_value,
    changeLabel: indicator.change_label,
    trend: indicator.trend,
    frequency: indicator.frequency,
    sourceLabel: indicator.source_label,
    updatedAt: indicator.updated_at,
    periodLabel: indicator.period_label,
    context: indicator.context,
  };
}
