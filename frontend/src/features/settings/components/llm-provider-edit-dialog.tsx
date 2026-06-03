import { FormEvent, useState } from "react";
import type { LlmProviderPayload } from "../model/llm-settings.types";

type LlmProviderEditDialogProps = {
  onCancel: () => void;
  onSave: (payload: LlmProviderPayload) => void;
  isSaving: boolean;
};

/** 渲染新增 LLM provider 表单。 */
export function LlmProviderEditDialog({ onCancel, onSave, isSaving }: LlmProviderEditDialogProps) {
  const [form, setForm] = useState<LlmProviderPayload>({
    name: "",
    providerType: "openai_compatible",
    baseUrl: "",
    modelName: "",
    apiKey: "",
    timeoutSeconds: 60,
  });

  /** 提交新增配置。 */
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSave(form);
  }

  return (
    <form className="rounded-lg border border-blue-100 bg-blue-50/50 p-4" onSubmit={handleSubmit}>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="grid gap-2 text-xs font-semibold text-slate-700">
          配置名称
          <input className="h-9 rounded-md border border-slate-300 px-3 font-normal" onChange={(event) => setForm({ ...form, name: event.target.value })} value={form.name} />
        </label>
        <label className="grid gap-2 text-xs font-semibold text-slate-700">
          服务类型
          <select className="h-9 rounded-md border border-slate-300 px-3 font-normal" onChange={(event) => setForm({ ...form, providerType: event.target.value })} value={form.providerType}>
            <option value="openai_compatible">OpenAI Compatible</option>
          </select>
        </label>
        <label className="grid gap-2 text-xs font-semibold text-slate-700 md:col-span-2">
          Base URL
          <input className="h-9 rounded-md border border-slate-300 px-3 font-normal" onChange={(event) => setForm({ ...form, baseUrl: event.target.value })} value={form.baseUrl} />
        </label>
        <label className="grid gap-2 text-xs font-semibold text-slate-700">
          模型名称
          <input className="h-9 rounded-md border border-slate-300 px-3 font-normal" onChange={(event) => setForm({ ...form, modelName: event.target.value })} value={form.modelName} />
        </label>
        <label className="grid gap-2 text-xs font-semibold text-slate-700">
          API Key
          <input className="h-9 rounded-md border border-slate-300 px-3 font-normal" onChange={(event) => setForm({ ...form, apiKey: event.target.value })} type="password" value={form.apiKey} />
        </label>
      </div>
      <div className="mt-4 flex justify-end gap-2">
        <button className="rounded-md border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700" onClick={onCancel} type="button">取消</button>
        <button className="rounded-md bg-blue-600 px-3 py-2 text-xs font-semibold text-white" disabled={isSaving} type="submit">保存配置</button>
      </div>
    </form>
  );
}
