import type { EventInsightTopicsPayload } from "../model/event-insight.types";

/** 拉取 Event Insight 主题列表。 */
export async function getEventInsightTopics(signal?: AbortSignal): Promise<EventInsightTopicsPayload> {
  const response = await fetch("/api/frontend/modules/event-insight/topics", {
    signal,
  });

  if (!response.ok) {
    throw new Error("Event Insight topics request failed");
  }

  return (await response.json()) as EventInsightTopicsPayload;
}
