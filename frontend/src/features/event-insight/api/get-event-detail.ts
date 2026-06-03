import type { EventInsightEventDetailPayload } from "../model/event-insight.types";

/** 拉取单个 Event Insight 事件详情。 */
export async function getEventInsightEventDetail(eventId: number, signal?: AbortSignal): Promise<EventInsightEventDetailPayload> {
  const response = await fetch(`/api/frontend/modules/event-insight/events/${eventId}`, {
    signal,
  });

  if (!response.ok) {
    throw new Error("Event Insight event detail request failed");
  }

  return (await response.json()) as EventInsightEventDetailPayload;
}
