import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createLlmProvider, getLlmProviders, getLlmTaskConfigs, testLlmProvider } from "../api/llm-settings-api";

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

/** 测试 provider 连接。 */
export function useTestLlmProviderMutation() {
  return useMutation({
    mutationFn: testLlmProvider,
  });
}
