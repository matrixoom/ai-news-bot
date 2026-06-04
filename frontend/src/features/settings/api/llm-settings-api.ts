import type { LlmProviderConfig, LlmProviderPayload, LlmTaskConfig, RssSchedulerConfig, RssSourceConfig, RssSourcePayload } from "../model/llm-settings.types";

/** 拉取脱敏后的 LLM provider 列表。 */
export async function getLlmProviders(signal?: AbortSignal): Promise<{ providers: LlmProviderConfig[] }> {
  const response = await fetch("/api/system/llm/providers", { signal });
  if (!response.ok) throw new Error("LLM providers request failed");
  return (await response.json()) as { providers: LlmProviderConfig[] };
}

/** 创建 LLM provider 配置。 */
export async function createLlmProvider(payload: LlmProviderPayload): Promise<{ provider: LlmProviderConfig }> {
  const response = await fetch("/api/system/llm/providers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("LLM provider create request failed");
  return (await response.json()) as { provider: LlmProviderConfig };
}

/** 更新 LLM provider 配置。 */
export async function updateLlmProvider(providerId: number, payload: LlmProviderPayload): Promise<{ provider: LlmProviderConfig }> {
  const response = await fetch(`/api/system/llm/providers/${providerId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("LLM provider update request failed");
  return (await response.json()) as { provider: LlmProviderConfig };
}

/** 禁用 LLM provider 配置。 */
export async function disableLlmProvider(providerId: number): Promise<{ provider: LlmProviderConfig }> {
  const response = await fetch(`/api/system/llm/providers/${providerId}/disable`, { method: "POST" });
  if (!response.ok) throw new Error("LLM provider disable request failed");
  return (await response.json()) as { provider: LlmProviderConfig };
}

/** 测试 LLM provider 连接。 */
export async function testLlmProvider(providerId: number): Promise<{ ok: boolean; detail: string }> {
  const response = await fetch(`/api/system/llm/providers/${providerId}/test`, { method: "POST" });
  if (!response.ok) throw new Error("LLM provider test request failed");
  return (await response.json()) as { ok: boolean; detail: string };
}

/** 拉取 LLM 任务映射列表。 */
export async function getLlmTaskConfigs(signal?: AbortSignal): Promise<{ taskConfigs: LlmTaskConfig[] }> {
  const response = await fetch("/api/system/llm/task-configs", { signal });
  if (!response.ok) throw new Error("LLM task configs request failed");
  return (await response.json()) as { taskConfigs: LlmTaskConfig[] };
}

/** 拉取 RSS 源与调度配置。 */
export async function getRssSources(signal?: AbortSignal): Promise<{ sources: RssSourceConfig[]; scheduler: RssSchedulerConfig }> {
  const response = await fetch("/api/system/rss/sources", { signal });
  if (!response.ok) throw new Error("RSS sources request failed");
  return (await response.json()) as { sources: RssSourceConfig[]; scheduler: RssSchedulerConfig };
}

/** 创建 RSS 源配置。 */
export async function createRssSource(payload: RssSourcePayload): Promise<{ source: RssSourceConfig }> {
  const response = await fetch("/api/system/rss/sources", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("RSS source create request failed");
  return (await response.json()) as { source: RssSourceConfig };
}

/** 更新 RSS 源配置。 */
export async function updateRssSource(sourceId: number, payload: RssSourcePayload): Promise<{ source: RssSourceConfig }> {
  const response = await fetch(`/api/system/rss/sources/${sourceId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("RSS source update request failed");
  return (await response.json()) as { source: RssSourceConfig };
}

/** 删除 RSS 源配置。 */
export async function deleteRssSource(sourceId: number): Promise<{ source: RssSourceConfig }> {
  const response = await fetch(`/api/system/rss/sources/${sourceId}`, { method: "DELETE" });
  if (!response.ok) throw new Error("RSS source delete request failed");
  return (await response.json()) as { source: RssSourceConfig };
}

/** 手动抓取 RSS 源。 */
export async function fetchRssSource(sourceId: number): Promise<{ importedCount: number; skippedCount: number }> {
  const response = await fetch(`/api/system/rss/sources/${sourceId}/fetch`, { method: "POST" });
  if (!response.ok) throw new Error("RSS source fetch request failed");
  return (await response.json()) as { importedCount: number; skippedCount: number };
}
