import type { EventGraphPayload } from "../model/event-insight.types";

/** 拉取 Event Insight 事件关系图投影。 */
export async function getEventInsightGraph(topicId?: number, signal?: AbortSignal): Promise<EventGraphPayload> {
  const params = new URLSearchParams();
  if (topicId !== undefined) params.set("topicId", String(topicId));

  const response = await fetch(`/api/frontend/modules/event-insight/graph?${params.toString()}`, {
    signal,
  });

  if (!response.ok) {
    throw new Error("Event Insight graph request failed");
  }

  return (await response.json()) as EventGraphPayload;
}
