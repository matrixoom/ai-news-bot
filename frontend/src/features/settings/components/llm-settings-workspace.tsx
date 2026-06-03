import { PlusIcon, SignalIcon } from "@heroicons/react/24/outline";
import { useEffect, useState } from "react";
import { useCreateLlmProviderMutation, useLlmProvidersQuery, useLlmTaskConfigsQuery, useTestLlmProviderMutation } from "../hooks/use-llm-settings-queries";
import type { LlmProviderPayload } from "../model/llm-settings.types";
import { LlmProviderEditDialog } from "./llm-provider-edit-dialog";
import { LlmProviderTable } from "./llm-provider-table";
import { LlmTaskMappingTable } from "./llm-task-mapping-table";

/** 渲染真实 API 驱动的大模型配置工作台。 */
export function LlmSettingsWorkspace() {
  const providersQuery = useLlmProvidersQuery();
  const taskConfigsQuery = useLlmTaskConfigsQuery();
  const createProvider = useCreateLlmProviderMutation();
  const testProvider = useTestLlmProviderMutation();
  const providers = providersQuery.data?.providers ?? [];
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const selectedProvider = providers.find((provider) => provider.id === selectedId) ?? providers[0];
  const connectionDetail = testProvider.data?.detail;

  useEffect(() => {
    if (selectedId === null && providers.length > 0) {
      setSelectedId(providers[0].id);
    }
  }, [providers, selectedId]);

  /** 保存新增 provider，成功后关闭表单。 */
  function handleSaveProvider(payload: LlmProviderPayload) {
    createProvider.mutate(payload, {
      onSuccess: () => setShowCreateForm(false),
    });
  }

  return (
    <section className="space-y-4">
      <header className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-slate-950">大模型配置</h2>
          <p className="mt-1 max-w-4xl text-sm leading-6 text-slate-500">统一管理事件抽取、聚类、主题摘要和关系判断所使用的模型服务。密钥只在保存时提交，列表与编辑响应均不返回明文。</p>
        </div>
        <button className="inline-flex items-center rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700" onClick={() => setShowCreateForm(true)} type="button">
          <PlusIcon aria-hidden="true" className="mr-1 h-4 w-4" />
          新增配置
        </button>
      </header>

      <div className="grid gap-3 xl:grid-cols-[290px_minmax(0,1fr)]">
        <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
            <h3 className="text-sm font-semibold text-slate-950">模型服务</h3>
            <span className="text-xs text-slate-500">{providersQuery.isLoading ? "加载中" : `${providers.length} 个配置`}</span>
          </header>
          {providersQuery.isError ? (
            <div className="p-4 text-sm text-rose-600">模型配置加载失败。</div>
          ) : (
            <LlmProviderTable onSelect={setSelectedId} providers={providers} selectedId={selectedProvider?.id ?? null} />
          )}
        </section>

        <div className="space-y-3">
          {showCreateForm ? (
            <LlmProviderEditDialog isSaving={createProvider.isPending} onCancel={() => setShowCreateForm(false)} onSave={handleSaveProvider} />
          ) : null}

          <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
              <h3 className="text-sm font-semibold text-slate-950">{selectedProvider?.name ?? "未选择模型服务"}</h3>
              <span className="rounded-full bg-green-100 px-2 py-1 text-[11px] font-semibold text-green-700">真实配置</span>
            </header>
            <div className="space-y-4 p-4 text-xs text-slate-600">
              {selectedProvider ? (
                <>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div><strong className="block text-slate-500">服务类型</strong>{selectedProvider.providerType}</div>
                    <div><strong className="block text-slate-500">模型名称</strong>{selectedProvider.modelName}</div>
                    <div className="md:col-span-2"><strong className="block text-slate-500">Base URL</strong>{selectedProvider.baseUrl || "默认 OpenAI endpoint"}</div>
                    <div><strong className="block text-slate-500">API Key</strong>{selectedProvider.apiKeyPreview || "未配置"}</div>
                    <div><strong className="block text-slate-500">请求超时</strong>{selectedProvider.timeoutSeconds} 秒</div>
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4">
                    <span className="inline-flex items-center font-semibold text-slate-700">
                      <SignalIcon aria-hidden="true" className="mr-1 h-4 w-4" />
                      {connectionDetail ?? "连接状态待测试"}
                    </span>
                    <button className="rounded-md border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700" onClick={() => testProvider.mutate(selectedProvider.id)} type="button">
                      测试连接
                    </button>
                  </div>
                </>
              ) : (
                <div>暂无模型配置。</div>
              )}
            </div>
          </section>

          <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            <header className="border-b border-slate-200 px-4 py-3">
              <h3 className="text-sm font-semibold text-slate-950">任务默认模型</h3>
            </header>
            {taskConfigsQuery.isLoading ? (
              <div className="p-4 text-sm text-slate-500">正在加载任务映射...</div>
            ) : (
              <LlmTaskMappingTable taskConfigs={taskConfigsQuery.data?.taskConfigs ?? []} />
            )}
          </section>
        </div>
      </div>
    </section>
  );
}
