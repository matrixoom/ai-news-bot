import type { LlmProviderConfig } from "../model/llm-settings.types";

type LlmProviderTableProps = {
  providers: LlmProviderConfig[];
  selectedId: number | null;
  onSelect: (providerId: number) => void;
};

/** 渲染 LLM provider 列表。 */
export function LlmProviderTable({ providers, selectedId, onSelect }: LlmProviderTableProps) {
  if (providers.length === 0) {
    return <div className="p-4 text-sm text-slate-500">暂无模型配置，请先新增 provider。</div>;
  }

  return (
    <div className="space-y-1 p-2">
      {providers.map((provider) => (
        <button
          className={`w-full rounded-md border p-3 text-left ${selectedId === provider.id ? "border-blue-200 bg-blue-50" : "border-transparent hover:bg-slate-50"}`}
          key={provider.id}
          onClick={() => onSelect(provider.id)}
          type="button"
        >
          <strong className="block text-xs text-slate-950">{provider.name}</strong>
          <span className="mt-1 block text-[11px] text-slate-500">
            {provider.providerType} · {provider.enabled ? "已启用" : "未启用"} · {provider.apiKeyPreview || "未配置密钥"}
          </span>
        </button>
      ))}
    </div>
  );
}
