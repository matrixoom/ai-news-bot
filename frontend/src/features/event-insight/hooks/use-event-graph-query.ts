import { useQuery } from "@tanstack/react-query";
import { getEventInsightGraph } from "../api/get-event-graph";

/** 查询 Event Insight 事件关系图。 */
export function useEventGraphQuery(topicId?: number) {
  return useQuery({
    queryKey: ["event-insight-graph", topicId],
    queryFn: ({ signal }) => getEventInsightGraph(topicId, signal),
  });
}
