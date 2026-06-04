import { useQuery } from "@tanstack/react-query";
import { getEventInsightGraph } from "../api/get-event-graph";

/** 查询 Event Insight 事件关系图。 */
export function useEventGraphQuery() {
  return useQuery({
    queryKey: ["event-insight-graph"],
    queryFn: ({ signal }) => getEventInsightGraph(signal),
  });
}
