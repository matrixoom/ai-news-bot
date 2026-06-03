import type { EventInsightEventDetailPayload } from "../model/event-insight.types";

export type UpdateEventInsightEventPayload = {
  title?: string;
  summary?: string;
  eventType?: string;
  confidenceScore?: number;
  reason?: string;
};

/** 写入事件人工字段覆盖。 */
export async function updateEventInsightEvent(eventId: number, payload: UpdateEventInsightEventPayload): Promise<EventInsightEventDetailPayload> {
  const response = await fetch(`/api/frontend/modules/event-insight/events/${eventId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Event Insight event update request failed");
  }

  return (await response.json()) as EventInsightEventDetailPayload;
}
