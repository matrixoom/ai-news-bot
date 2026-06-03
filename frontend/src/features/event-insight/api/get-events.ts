import type { EventInsightEventsPayload, EventInsightEventsQuery } from "../model/event-insight.types";

/** 拉取 Event Insight 事件分页列表。 */
export async function getEventInsightEvents(options: EventInsightEventsQuery & { signal?: AbortSignal } = {}): Promise<EventInsightEventsPayload> {
  const params = new URLSearchParams({
    page: String(options.page ?? 1),
    pageSize: String(options.pageSize ?? 20),
    status: options.status ?? "active",
    sortBy: options.sortBy ?? "event_time",
    sortOrder: options.sortOrder ?? "desc",
  });
  if (options.keyword) params.set("keyword", options.keyword);
  if (options.topicId !== undefined) params.set("topicId", String(options.topicId));

  const response = await fetch(`/api/frontend/modules/event-insight/events?${params.toString()}`, {
    signal: options.signal,
  });

  if (!response.ok) {
    throw new Error("Event Insight events request failed");
  }

  return (await response.json()) as EventInsightEventsPayload;
}
