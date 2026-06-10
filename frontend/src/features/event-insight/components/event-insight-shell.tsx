import type { ReactNode } from "react";
import type { InsightTone } from "../model/event-insight.types";

const TONE_CLASSES: Record<InsightTone, string> = {
  blue: "bg-blue-100 text-blue-700",
  green: "bg-emerald-100 text-emerald-700",
  amber: "bg-amber-100 text-amber-700",
  rose: "bg-rose-100 text-rose-700",
  violet: "bg-violet-100 text-violet-700",
  slate: "bg-slate-100 text-slate-600",
};

/**
 * 渲染事件洞察工作台统一标题区。
 *
 * @param props 标题、说明、操作区与页面主体。
 * @returns 事件洞察页面布局。
 */
export function EventInsightShell({
  title,
  description,
  actions,
  children,
}: {
  title: string;
  description: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="space-y-4">
      <header className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-ink">{title}</h2>
          <p className="mt-1 max-w-4xl text-sm leading-6 text-muted">{description}</p>
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </header>
      {children}
    </section>
  );
}

/**
 * 渲染事件洞察页面通用面板。
 *
 * @param props 面板标题、辅助内容和主体。
 * @returns 带边框和轻阴影的面板。
 */
export function InsightPanel({
  title,
  aside,
  className = "",
  children,
}: {
  title?: string;
  aside?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={`workbench-panel overflow-hidden ${className}`}>
      {title || aside ? (
        <header className="flex min-h-12 items-center justify-between gap-3 border-b border-line px-4 py-3">
          {title ? <h3 className="text-sm font-semibold text-ink">{title}</h3> : <span />}
          {aside}
        </header>
      ) : null}
      {children}
    </section>
  );
}

/**
 * 渲染低饱和状态标签。
 *
 * @param props 标签文本与色调。
 * @returns 状态标签。
 */
export function InsightBadge({ children, tone = "slate" }: { children: ReactNode; tone?: InsightTone }) {
  return <span className={`inline-flex rounded-full px-2 py-1 text-[11px] font-semibold ${TONE_CLASSES[tone]}`}>{children}</span>;
}
