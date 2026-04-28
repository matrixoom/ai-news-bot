import type { EventsModuleRawPayload } from "../model/events-module.types";

export async function getEventsModule(signal?: AbortSignal): Promise<EventsModuleRawPayload> {
  const response = await fetch("/api/frontend/dashboard", {
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new Error(`events request failed: ${response.status}`);
  }

  return normalizeEventsPayload(await response.json());
}

/**
 * 将 Dashboard 聚合 payload 转为 Events 页面沿用的视图 payload。
 * 参数 rawPayload 表示后端返回的聚合数据或旧模块数据。
 * 返回 Events 模块页面可直接消费的稳定结构。
 */
function normalizeEventsPayload(rawPayload: unknown): EventsModuleRawPayload {
  const payload = rawPayload as EventsModuleRawPayload & {
    event_sections?: Array<EventsModuleRawPayload["module"]["details"][number]["section"]>;
  };

  if (payload.module?.id === "events") {
    return payload;
  }

  const sections = payload.event_sections ?? [];

  return {
    generated_at: payload.generated_at,
    module: {
      id: "events",
      label: "事件展望",
      note: `${sections.length} 个窗口`,
      description: "未来展望",
      status: sections.some((section) => section.status === "live") ? "live" : (sections[0]?.status ?? "compatible"),
      loading: false,
      details: sections.map((section) => ({
        id: section.key,
        label: section.title,
        kind: "events",
        note: `${section.items.length} 条`,
        section,
      })),
    },
  };
}
