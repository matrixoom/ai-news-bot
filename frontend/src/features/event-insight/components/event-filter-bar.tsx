import { FunnelIcon } from "@heroicons/react/24/outline";
import { FormEvent, useState } from "react";

type EventFilterBarProps = {
  keyword: string;
  status: "active" | "ignored" | "archived" | "all";
  onApply: (filters: { keyword: string; status: "active" | "ignored" | "archived" | "all" }) => void;
};

/** 渲染事件列表筛选条。 */
export function EventFilterBar({ keyword, status, onApply }: EventFilterBarProps) {
  const [draftKeyword, setDraftKeyword] = useState(keyword);
  const [draftStatus, setDraftStatus] = useState(status);

  /** 提交当前筛选条件。 */
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onApply({ keyword: draftKeyword.trim(), status: draftStatus });
  }

  return (
    <form className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white p-3" onSubmit={handleSubmit}>
      <div className="flex flex-wrap gap-2">
        <input
          aria-label="搜索事件"
          className="h-9 w-64 rounded-md border border-slate-300 px-3 text-xs text-slate-700"
          onChange={(event) => setDraftKeyword(event.target.value)}
          placeholder="搜索事件、公司或主题"
          value={draftKeyword}
        />
        <select
          aria-label="事件状态"
          className="h-9 rounded-md border border-slate-300 px-3 text-xs text-slate-700"
          onChange={(event) => setDraftStatus(event.target.value as EventFilterBarProps["status"])}
          value={draftStatus}
        >
          <option value="active">活跃事件</option>
          <option value="ignored">已忽略</option>
          <option value="archived">已归档</option>
          <option value="all">全部状态</option>
        </select>
      </div>
      <button className="rounded-md bg-slate-900 px-3 py-2 text-xs font-semibold text-white" type="submit">
        <FunnelIcon aria-hidden="true" className="mr-1 inline h-4 w-4" />
        筛选
      </button>
    </form>
  );
}
