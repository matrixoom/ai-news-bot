import { useQuery } from "@tanstack/react-query";
import { getEventInsightEvents } from "../api/get-events";
import type { EventInsightEventsQuery } from "../model/event-insight.types";

/** 查询 Event Insight 事件分页列表。 */
export function useEventInsightEventsQuery(query: EventInsightEventsQuery) {
  return useQuery({
    queryKey: ["event-insight-events", query],
    queryFn: ({ signal }) => getEventInsightEvents({ ...query, signal }),
  });
}
