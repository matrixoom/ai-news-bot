import { ArrowPathIcon, PencilSquareIcon, PlusIcon, TrashIcon } from "@heroicons/react/24/outline";
import { FormEvent, useState } from "react";
import { useCreateRssSourceMutation, useDeleteRssSourceMutation, useFetchRssSourceMutation, useRssSourcesQuery, useUpdateRssSourceMutation } from "../hooks/use-llm-settings-queries";
import type { RssSourceConfig, RssSourcePayload } from "../model/llm-settings.types";

/** 渲染 System 中独立的 RSS 源配置工作台。 */
export function RssSettingsWorkspace() {
  const sourcesQuery = useRssSourcesQuery();
  const createSource = useCreateRssSourceMutation();
  const updateSource = useUpdateRssSourceMutation();
  const deleteSource = useDeleteRssSourceMutation();
  const fetchSource = useFetchRssSourceMutation();
  const sources = sourcesQuery.data?.sources ?? [];
  const [editingSource, setEditingSource] = useState<RssSourceConfig | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [message, setMessage] = useState("");

  /** 保存新增 RSS 源。 */
  function handleCreate(payload: RssSourcePayload) {
    createSource.mutate(payload, {
      onSuccess: () => {
        setShowCreateForm(false);
        setMessage("RSS 源已新增。");
      },
    });
  }

  /** 保存已有 RSS 源。 */
  function handleUpdate(payload: RssSourcePayload) {
    if (!editingSource) return;
    updateSource.mutate(
      { sourceId: editingSource.id, payload },
      {
        onSuccess: () => {
          setEditingSource(null);
          setMessage("RSS 源已更新。");
        },
      },
    );
  }

  /** 删除 RSS 源，后端保留软删除记录。 */
  function handleDelete(source: RssSourceConfig) {
    deleteSource.mutate(source.id, {
      onSuccess: () => setMessage(`RSS 源已删除：${source.name}`),
    });
  }

  /** 手动抓取指定 RSS 源并显示导入结果。 */
  function handleFetch(source: RssSourceConfig) {
    fetchSource.mutate(source.id, {
      onSuccess: (result) => setMessage(`抓取完成：${result.importedCount} 条新增，${result.skippedCount} 条跳过。`),
    });
  }

  return (
    <section className="space-y-4">
      <header className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-slate-950">RSS 源配置</h2>
          <p className="mt-1 max-w-4xl text-sm leading-6 text-slate-500">
            管理新闻抓取源。首次打开会载入代码中原有的默认 RSS 源，后续新增、修改和删除都以数据库配置为准。
          </p>
          <p className="mt-1 text-xs text-slate-500">每日 {sourcesQuery.data?.scheduler.dailyFetchTime ?? "06:30"} · {sourcesQuery.data?.scheduler.timezone ?? "Asia/Shanghai"}</p>
        </div>
        <button className="inline-flex items-center rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700" onClick={() => setShowCreateForm(true)} type="button">
          <PlusIcon aria-hidden="true" className="mr-1 h-4 w-4" />
          新增 RSS 源
        </button>
      </header>

      {message ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</div> : null}
      {sourcesQuery.isError ? <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">RSS 源加载失败。</div> : null}

      {showCreateForm ? <RssSourceForm isSaving={createSource.isPending} onCancel={() => setShowCreateForm(false)} onSave={handleCreate} /> : null}
      {editingSource ? <RssSourceForm initialValue={editingSource} isSaving={updateSource.isPending} onCancel={() => setEditingSource(null)} onSave={handleUpdate} /> : null}

      <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-950">已配置源</h3>
          <span className="text-xs text-slate-500">{sourcesQuery.isLoading ? "加载中" : `${sources.length} 个 RSS 源`}</span>
        </header>
        <div className="divide-y divide-slate-100">
          {sourcesQuery.isLoading ? <div className="p-4 text-sm text-slate-500">正在加载 RSS 源...</div> : null}
          {sources.length === 0 && !sourcesQuery.isLoading ? <div className="p-4 text-sm text-slate-500">暂无 RSS 源。</div> : null}
          {sources.map((source) => (
            <article className="grid gap-3 p-4 text-xs lg:grid-cols-[minmax(0,1fr)_auto]" key={source.id}>
              <div className="min-w-0">
                <h4 className="truncate text-sm font-semibold text-slate-950">{source.name}</h4>
                <p className="mt-1 break-all text-slate-500">{source.url}</p>
                <p className="mt-2 text-slate-500">{source.language} · {source.category} · {source.enabled ? "已启用" : "已停用"} · {source.fetchTime} · 每次 {source.maxItems} 条</p>
              </div>
              <div className="flex flex-wrap items-center gap-2 lg:justify-end">
                <button className="inline-flex items-center rounded-md border border-slate-300 px-3 py-2 font-semibold text-slate-700 disabled:opacity-60" disabled={fetchSource.isPending} onClick={() => handleFetch(source)} type="button">
                  <ArrowPathIcon aria-hidden="true" className="mr-1 h-4 w-4" />
                  抓取 {source.name}
                </button>
                <button className="inline-flex items-center rounded-md border border-slate-300 px-3 py-2 font-semibold text-slate-700" onClick={() => setEditingSource(source)} type="button">
                  <PencilSquareIcon aria-hidden="true" className="mr-1 h-4 w-4" />
                  编辑 {source.name}
                </button>
                <button className="inline-flex items-center rounded-md border border-rose-200 px-3 py-2 font-semibold text-rose-700 disabled:opacity-60" disabled={deleteSource.isPending} onClick={() => handleDelete(source)} type="button">
                  <TrashIcon aria-hidden="true" className="mr-1 h-4 w-4" />
                  删除 {source.name}
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}

type RssSourceFormProps = {
  initialValue?: RssSourceConfig;
  isSaving: boolean;
  onCancel: () => void;
  onSave: (payload: RssSourcePayload) => void;
};

/** 渲染 RSS 源新增或编辑表单。 */
function RssSourceForm({ initialValue, isSaving, onCancel, onSave }: RssSourceFormProps) {
  const [form, setForm] = useState<RssSourcePayload>({
    name: initialValue?.name ?? "",
    url: initialValue?.url ?? "",
    language: initialValue?.language ?? "zh",
    category: initialValue?.category ?? "finance",
    enabled: initialValue?.enabled ?? true,
    fetchTime: initialValue?.fetchTime ?? "06:30",
    maxItems: initialValue?.maxItems ?? 20,
  });

  /** 提交 RSS 源表单。 */
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSave(form);
  }

  return (
    <form className="rounded-lg border border-blue-100 bg-blue-50/50 p-4" onSubmit={handleSubmit}>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <label className="grid gap-2 text-xs font-semibold text-slate-700">
          RSS 名称
          <input className="h-9 rounded-md border border-slate-300 px-3 font-normal" onChange={(event) => setForm({ ...form, name: event.target.value })} required value={form.name} />
        </label>
        <label className="grid gap-2 text-xs font-semibold text-slate-700 md:col-span-2">
          RSS URL
          <input className="h-9 rounded-md border border-slate-300 px-3 font-normal" onChange={(event) => setForm({ ...form, url: event.target.value })} required type="url" value={form.url} />
        </label>
        <label className="grid gap-2 text-xs font-semibold text-slate-700">
          语言
          <input className="h-9 rounded-md border border-slate-300 px-3 font-normal" onChange={(event) => setForm({ ...form, language: event.target.value })} value={form.language} />
        </label>
        <label className="grid gap-2 text-xs font-semibold text-slate-700">
          分类
          <input className="h-9 rounded-md border border-slate-300 px-3 font-normal" onChange={(event) => setForm({ ...form, category: event.target.value })} value={form.category} />
        </label>
        <label className="grid gap-2 text-xs font-semibold text-slate-700">
          抓取时间
          <input className="h-9 rounded-md border border-slate-300 px-3 font-normal" onChange={(event) => setForm({ ...form, fetchTime: event.target.value })} type="time" value={form.fetchTime} />
        </label>
        <label className="grid gap-2 text-xs font-semibold text-slate-700">
          每次条数
          <input className="h-9 rounded-md border border-slate-300 px-3 font-normal" max={100} min={1} onChange={(event) => setForm({ ...form, maxItems: Number(event.target.value) })} type="number" value={form.maxItems} />
        </label>
        <label className="flex items-center gap-2 text-xs font-semibold text-slate-700">
          <input checked={form.enabled} onChange={(event) => setForm({ ...form, enabled: event.target.checked })} type="checkbox" />
          启用
        </label>
      </div>
      <div className="mt-3 flex justify-end gap-2">
        <button className="rounded-md border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700" onClick={onCancel} type="button">取消</button>
        <button className="rounded-md bg-blue-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-60" disabled={isSaving} type="submit">保存 RSS 源</button>
      </div>
    </form>
  );
}
