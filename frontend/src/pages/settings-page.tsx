import { CircleStackIcon, CpuChipIcon } from "@heroicons/react/24/outline";
import { useState } from "react";
import { LlmSettingsWorkspace } from "../features/settings/components/llm-settings-workspace";
import { RssSettingsWorkspace } from "../features/settings/components/rss-settings-workspace";

type SettingsTab = "llm" | "rss";

const SETTINGS_TABS: Array<{ id: SettingsTab; label: string; icon: typeof CpuChipIcon }> = [
  { id: "llm", label: "大模型配置", icon: CpuChipIcon },
  { id: "rss", label: "RSS 源配置", icon: CircleStackIcon },
];

/** 渲染系统设置页。 */
export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("llm");

  return (
    <section className="grid gap-4 lg:grid-cols-[190px_minmax(0,1fr)]">
      <div className="workbench-panel flex h-fit flex-col p-1" role="tablist" aria-label="系统配置">
        {SETTINGS_TABS.map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              aria-selected={active}
              className={`inline-flex items-center rounded-control px-3 py-2.5 text-sm font-semibold ${active ? "bg-accent-soft text-accent" : "text-muted hover:bg-surface-subtle hover:text-ink"}`}
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              role="tab"
              type="button"
            >
              <Icon aria-hidden="true" className="mr-2 h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>
      <div className="min-w-0" role="tabpanel">
        {activeTab === "llm" ? <LlmSettingsWorkspace /> : <RssSettingsWorkspace />}
      </div>
    </section>
  );
}
