import { PlusIcon, SignalIcon } from "@heroicons/react/24/outline";
import { FormEvent } from "react";
import { useEffect, useState } from "react";
import { useCreateLlmProviderMutation, useCreateRssSourceMutation, useDisableLlmProviderMutation, useFetchRssSourceMutation, useLlmProvidersQuery, useLlmTaskConfigsQuery, useRssSourcesQuery, useTestLlmProviderMutation, useUpdateLlmProviderMutation } from "../hooks/use-llm-settings-queries";
import type { LlmProviderPayload, RssSourcePayload } from "../model/llm-settings.types";
import { LlmProviderEditDialog } from "./llm-provider-edit-dialog";
import { LlmProviderTable } from "./llm-provider-table";
import { LlmTaskMappingTable } from "./llm-task-mapping-table";

/** 渲染真实 API 驱动的大模型配置工作台。 */
export function LlmSettingsWorkspace() {
  const providersQuery = useLlmProvidersQuery();
  const taskConfigsQuery = useLlmTaskConfigsQuery();
  const rssSourcesQuery = useRssSourcesQuery();
  const createProvider = useCreateLlmProviderMutation();
  const updateProvider = useUpdateLlmProviderMutation();
  const disableProvider = useDisableLlmProviderMutation();
  const testProvider = useTestLlmProviderMutation();
  const createRssSource = useCreateRssSourceMutation();
  const fetchRssSource = useFetchRssSourceMutation();
  const providers = providersQuery.data?.providers ?? [];
  const rssSources = rssSourcesQuery.data?.sources ?? [];
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [showRssForm, setShowRssForm] = useState(false);
  const [settingsMessage, setSettingsMessage] = useState("");
  const selectedProvider = providers.find((provider) => provider.id === selectedId) ?? providers[0];
  const connectionStatus = testProvider.isPending
    ? "testing"
    : testProvider.data?.ok
      ? "success"
      : testProvider.data || testProvider.isError
        ? "failed"
        : "idle";
  const connectionDetail = testProvider.isPending
    ? "正在测试连接..."
    : testProvider.isError
      ? "连接测试请求失败，请稍后重试。"
      : testProvider.data?.detail ?? "连接状态待测试";
  const connectionClassName = {
    idle: "text-slate-700",
    testing: "text-blue-700",
    success: "text-emerald-700",
    failed: "text-rose-700",
  }[connectionStatus];

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

  /** 保存已有 provider，未填写密钥时后端保留旧密钥。 */
  function handleUpdateProvider(payload: LlmProviderPayload) {
    if (!selectedProvider) return;
    updateProvider.mutate({ providerId: selectedProvider.id, payload }, {
      onSuccess: () => {
        setShowEditForm(false);
        setSettingsMessage("");
      },
    });
  }

  /** 禁用当前 provider。 */
  function handleDisableProvider() {
    if (!selectedProvider) return;
    disableProvider.mutate(selectedProvider.id, {
      onSuccess: () => setSettingsMessage("模型配置已禁用。"),
    });
  }

  /** 保存新增 RSS 源。 */
  function handleSaveRssSource(payload: RssSourcePayload) {
    createRssSource.mutate(payload, {
      onSuccess: () => setShowRssForm(false),
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
          {showEditForm && selectedProvider ? (
            <LlmProviderEditDialog
              initialValue={selectedProvider}
              isSaving={updateProvider.isPending}
              onCancel={() => setShowEditForm(false)}
              onSave={handleUpdateProvider}
            />
          ) : null}
          {settingsMessage ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{settingsMessage}</div> : null}

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
                    <span className={`inline-flex items-center font-semibold ${connectionClassName}`}>
                      <SignalIcon aria-hidden="true" className="mr-1 h-4 w-4" />
                      {connectionDetail}
                    </span>
                    <button className="rounded-md border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-60" disabled={testProvider.isPending} onClick={() => testProvider.mutate(selectedProvider.id)} type="button">
                      {testProvider.isPending ? "测试中" : "测试连接"}
                    </button>
                  </div>
                  <div className="flex flex-wrap justify-end gap-2 border-t border-slate-200 pt-4">
                    <button className="rounded-md border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700" onClick={() => setShowEditForm(true)} type="button">编辑配置</button>
                    <button className="rounded-md border border-rose-200 px-3 py-2 text-xs font-semibold text-rose-700 disabled:opacity-60" disabled={disableProvider.isPending || !selectedProvider.enabled} onClick={handleDisableProvider} type="button">禁用配置</button>
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

          <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-950">RSS 源配置</h3>
                <p className="mt-1 text-xs text-slate-500">每日 {rssSourcesQuery.data?.scheduler.dailyFetchTime ?? "06:30"} · {rssSourcesQuery.data?.scheduler.timezone ?? "Asia/Shanghai"}</p>
              </div>
              <button className="rounded-md border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700" onClick={() => setShowRssForm(true)} type="button">新增 RSS 源</button>
            </header>
            <div className="space-y-3 p-4">
              {showRssForm ? <RssSourceForm isSaving={createRssSource.isPending} onCancel={() => setShowRssForm(false)} onSave={handleSaveRssSource} /> : null}
              {fetchRssSource.data ? <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">抓取完成：{fetchRssSource.data.importedCount} 条新增，{fetchRssSource.data.skippedCount} 条跳过。</div> : null}
              {rssSourcesQuery.isLoading ? <div className="text-sm text-slate-500">正在加载 RSS 源...</div> : null}
              {rssSources.length === 0 && !rssSourcesQuery.isLoading ? <div className="rounded-md border border-dashed border-slate-300 p-3 text-sm text-slate-500">暂无 RSS 源。</div> : null}
              {rssSources.map((source) => (
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-200 p-3 text-xs" key={source.id}>
                  <div>
                    <strong className="block text-slate-950">{source.name}</strong>
                    <span className="mt-1 block text-slate-500">{source.url} · {source.enabled ? "已启用" : "已禁用"} · {source.fetchTime}</span>
                  </div>
                  <button className="rounded-md border border-slate-300 px-3 py-2 font-semibold text-slate-700" disabled={fetchRssSource.isPending} onClick={() => fetchRssSource.mutate(source.id)} type="button">抓取 {source.name}</button>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </section>
  );
}

type RssSourceFormProps = {
  isSaving: boolean;
  onCancel: () => void;
  onSave: (payload: RssSourcePayload) => void;
};

/** 渲染 RSS 源新增表单。 */
function RssSourceForm({ isSaving, onCancel, onSave }: RssSourceFormProps) {
  const [form, setForm] = useState<RssSourcePayload>({
    name: "",
    url: "",
    language: "zh",
    category: "finance",
    enabled: true,
    fetchTime: "06:30",
    maxItems: 20,
  });

  /** 提交 RSS 源配置。 */
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSave(form);
  }

  return (
    <form className="rounded-lg border border-blue-100 bg-blue-50/50 p-4" onSubmit={handleSubmit}>
      <div className="grid gap-3 md:grid-cols-2">
        <label className="grid gap-2 text-xs font-semibold text-slate-700">
          RSS 名称
          <input className="h-9 rounded-md border border-slate-300 px-3 font-normal" onChange={(event) => setForm({ ...form, name: event.target.value })} value={form.name} />
        </label>
        <label className="grid gap-2 text-xs font-semibold text-slate-700">
          RSS URL
          <input className="h-9 rounded-md border border-slate-300 px-3 font-normal" onChange={(event) => setForm({ ...form, url: event.target.value })} value={form.url} />
        </label>
      </div>
      <div className="mt-3 flex justify-end gap-2">
        <button className="rounded-md border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700" onClick={onCancel} type="button">取消</button>
        <button className="rounded-md bg-blue-600 px-3 py-2 text-xs font-semibold text-white" disabled={isSaving} type="submit">保存 RSS 源</button>
      </div>
    </form>
  );
}
