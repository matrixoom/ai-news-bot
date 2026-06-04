import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { EventGraphWorkspace } from "../features/event-insight/components/event-graph-workspace";
import { EventListWorkspace } from "../features/event-insight/components/event-list-workspace";
import { TopicTraceWorkspace } from "../features/event-insight/components/topic-trace-workspace";
import { EventOutlookCalendarWorkspace } from "../features/event-outlook/components/event-outlook-calendar-workspace";
import type { EventOutlookRegion } from "../features/event-outlook/model/event-outlook.types";
import { resolveModuleTab, type ModuleTabDefinition } from "../shared/lib/module-tabs";

type EventOutlookWorkspaceTab = EventOutlookRegion | "events" | "topic-trace" | "event-graph";

const EVENT_OUTLOOK_WORKSPACE_TABS: readonly ModuleTabDefinition<EventOutlookWorkspaceTab>[] = [
  { value: "domestic", label: "国内" },
  { value: "international", label: "国际" },
  { value: "events", label: "事件列表" },
  { value: "topic-trace", label: "主题溯源" },
  { value: "event-graph", label: "关系网络" },
];

/**
 * 渲染 Event Outlook 页面，并隔离未来日历与事件洞察工作台。
 *
 * @returns 根据 URL Tab 选择后的工作区。
 */
export function EventOutlookPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = resolveModuleTab(searchParams.get("tab"), EVENT_OUTLOOK_WORKSPACE_TABS, "domestic");

  useEffect(() => {
    if (searchParams.get("tab") === activeTab) return;
    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.set("tab", activeTab);
    setSearchParams(nextSearchParams, { replace: true });
  }, [activeTab, searchParams, setSearchParams]);

  if (activeTab === "events") {
    return <EventListWorkspace />;
  }

  if (activeTab === "topic-trace") {
    return <TopicTraceWorkspace />;
  }

  if (activeTab === "event-graph") {
    return <EventGraphWorkspace />;
  }

  return <EventOutlookCalendarWorkspace region={activeTab} />;
}
