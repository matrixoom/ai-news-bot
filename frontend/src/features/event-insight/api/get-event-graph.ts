import type { EventGraphPayload } from "../model/event-insight.types";

/** 拉取 Event Insight 关系网络投影。 */
export async function getEventInsightGraph(signal?: AbortSignal): Promise<EventGraphPayload> {
  const response = await fetch("/api/frontend/modules/event-insight/graph", {
    signal,
  });

  if (!response.ok) {
    throw new Error("Event Insight graph request failed");
  }

  return (await response.json()) as EventGraphPayload;
}
