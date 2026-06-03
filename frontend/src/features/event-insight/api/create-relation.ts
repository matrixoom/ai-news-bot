export type CreateEventInsightRelationPayload = {
  sourceEventId: number;
  targetEventId: number;
  relationType: "same_topic" | "cause" | "support" | "contradict" | "follow_up";
  relationSummary: string;
  strengthScore: number;
  confidenceScore: number;
};

/** 创建 Event Insight 事件关系。 */
export async function createEventInsightRelation(payload: CreateEventInsightRelationPayload): Promise<{ traceId: string; relation: { id: number } }> {
  const response = await fetch("/api/frontend/modules/event-insight/relations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Event Insight relation create request failed");
  }

  return (await response.json()) as { traceId: string; relation: { id: number } };
}
