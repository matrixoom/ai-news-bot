import { useQuery } from "@tanstack/react-query";
import { getEventInsightEventDetail } from "../api/get-event-detail";

/** 查询 Event Insight 单个事件详情。 */
export function useEventDetailQuery(eventId: number | null) {
  return useQuery({
    queryKey: ["event-insight-event-detail", eventId],
    queryFn: ({ signal }) => getEventInsightEventDetail(eventId as number, signal),
    enabled: eventId !== null,
  });
}
