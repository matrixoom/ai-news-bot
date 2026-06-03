import type { EventInsightTopic } from "../model/event-insight.types";

export type CreateEventInsightTopicPayload = {
  name: string;
  summary?: string;
};

/** 创建 Event Insight 研究主题。 */
export async function createEventInsightTopic(payload: CreateEventInsightTopicPayload): Promise<{ traceId: string; topic: EventInsightTopic }> {
  const response = await fetch("/api/frontend/modules/event-insight/topics", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Event Insight topic create request failed");
  }

  return (await response.json()) as { traceId: string; topic: EventInsightTopic };
}
