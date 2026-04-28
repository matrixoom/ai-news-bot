import type { MarketModuleRawPayload } from "../model/market-module.types";

export async function getMarketModule(signal?: AbortSignal): Promise<MarketModuleRawPayload> {
  const response = await fetch("/api/frontend/dashboard", {
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new Error(`market request failed: ${response.status}`);
  }

  return normalizeMarketPayload(await response.json());
}

/**
 * 将 Dashboard 聚合 payload 转为 Market 页面沿用的视图 payload。
 * 参数 rawPayload 表示后端返回的聚合数据或旧模块数据。
 * 返回 Market 模块页面可直接消费的稳定结构。
 */
function normalizeMarketPayload(rawPayload: unknown): MarketModuleRawPayload {
  const payload = rawPayload as MarketModuleRawPayload & {
    market_sections?: Array<MarketModuleRawPayload["module"]["details"][number]["section"]>;
  };

  if (payload.module?.id === "market") {
    return payload;
  }

  const sections = payload.market_sections ?? [];

  return {
    generated_at: payload.generated_at,
    module: {
      id: "market",
      label: "市场模型",
      note: `${sections.length} 个模型`,
      description: "技术指标",
      status: sections.some((section) => section.status === "live") ? "live" : (sections[0]?.status ?? "compatible"),
      loading: false,
      details: sections.map((section) => ({
        id: section.key,
        label: section.label,
        kind: "market",
        note: section.signal,
        section,
      })),
    },
  };
}
