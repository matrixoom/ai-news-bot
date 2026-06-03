import { useQuery } from "@tanstack/react-query";
import { getEventInsightTopics } from "../api/get-topics";

/** 查询 Event Insight 主题列表。 */
export function useTopicsQuery() {
  return useQuery({
    queryKey: ["event-insight-topics"],
    queryFn: ({ signal }) => getEventInsightTopics(signal),
  });
}
