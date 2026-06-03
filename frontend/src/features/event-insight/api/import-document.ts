export type ImportEventInsightDocumentPayload = {
  mode: "text";
  title: string;
  content: string;
  sourceType: "news" | "other";
};

export type ImportEventInsightDocumentResult = {
  jobId: number;
  jobType: string;
  status: string;
  rawDocumentId?: number;
  traceId: string;
};

/** 导入文本材料并创建 Event Insight 本地处理任务。 */
export async function importEventInsightDocument(payload: ImportEventInsightDocumentPayload): Promise<ImportEventInsightDocumentResult> {
  const response = await fetch("/api/frontend/modules/event-insight/documents/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Event Insight document import request failed");
  }

  return (await response.json()) as ImportEventInsightDocumentResult;
}
