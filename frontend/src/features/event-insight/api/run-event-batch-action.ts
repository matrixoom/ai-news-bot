import type { EventInsightBatchActionPayload, EventInsightBatchActionResult } from "../model/event-insight.types";

/** 执行事件批量操作，后端会返回逐项成功和失败结果。 */
export async function runEventInsightBatchAction(payload: EventInsightBatchActionPayload): Promise<EventInsightBatchActionResult> {
  const response = await fetch("/api/frontend/modules/event-insight/events/batch-action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Event Insight batch action request failed");
  }

  return (await response.json()) as EventInsightBatchActionResult;
}
