import type { TopicTracePayload } from "../model/event-insight.types";

/** 拉取 Event Insight 主题溯源。 */
export async function getEventInsightTopicTrace(topicId: number, signal?: AbortSignal): Promise<TopicTracePayload> {
  const response = await fetch(`/api/frontend/modules/event-insight/topics/${topicId}/trace`, {
    signal,
  });

  if (!response.ok) {
    throw new Error("Event Insight topic trace request failed");
  }

  return (await response.json()) as TopicTracePayload;
}
