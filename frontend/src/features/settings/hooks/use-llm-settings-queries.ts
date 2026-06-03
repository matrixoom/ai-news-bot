import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createLlmProvider, createRssSource, disableLlmProvider, fetchRssSource, getLlmProviders, getLlmTaskConfigs, getRssSources, testLlmProvider, updateLlmProvider } from "../api/llm-settings-api";
import type { LlmProviderPayload } from "../model/llm-settings.types";

/** 查询 LLM provider 列表。 */
export function useLlmProvidersQuery() {
  return useQuery({
    queryKey: ["llm-providers"],
    queryFn: ({ signal }) => getLlmProviders(signal),
  });
}

/** 查询 LLM 任务映射列表。 */
export function useLlmTaskConfigsQuery() {
  return useQuery({
    queryKey: ["llm-task-configs"],
    queryFn: ({ signal }) => getLlmTaskConfigs(signal),
  });
}

/** 创建 provider 后刷新列表。 */
export function useCreateLlmProviderMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createLlmProvider,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["llm-providers"] }),
  });
}

/** 更新 provider 后刷新列表。 */
export function useUpdateLlmProviderMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ providerId, payload }: { providerId: number; payload: LlmProviderPayload }) => updateLlmProvider(providerId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["llm-providers"] }),
  });
}

/** 禁用 provider 后刷新列表。 */
export function useDisableLlmProviderMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: disableLlmProvider,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["llm-providers"] }),
  });
}

/** 测试 provider 连接。 */
export function useTestLlmProviderMutation() {
  return useMutation({
    mutationFn: testLlmProvider,
  });
}

/** 查询 RSS 源配置。 */
export function useRssSourcesQuery() {
  return useQuery({
    queryKey: ["rss-sources"],
    queryFn: ({ signal }) => getRssSources(signal),
  });
}

/** 创建 RSS 源后刷新列表。 */
export function useCreateRssSourceMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createRssSource,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rss-sources"] }),
  });
}

/** 抓取 RSS 源后刷新列表和事件列表。 */
export function useFetchRssSourceMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: fetchRssSource,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rss-sources"] });
      queryClient.invalidateQueries({ queryKey: ["event-insight-events"] });
    },
  });
}
