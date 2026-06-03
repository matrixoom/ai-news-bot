import { useQuery } from "@tanstack/react-query";
import { getEventInsightTopicTrace } from "../api/get-topic-trace";

/** 查询 Event Insight 主题溯源。 */
export function useTopicTraceQuery(topicId?: number) {
  return useQuery({
    queryKey: ["event-insight-topic-trace", topicId],
    queryFn: ({ signal }) => getEventInsightTopicTrace(topicId as number, signal),
    enabled: topicId !== undefined,
  });
}
