import type { ReactNode } from "react";

type ModulePageFrameProps = {
  title: string;
  description: string;
  toolbar?: ReactNode;
  lastUpdated?: ReactNode;
  main: ReactNode;
  side?: ReactNode;
  contentLayoutClassName?: string;
  showHeader?: boolean;
};

/** 渲染模块页面的通用内容框架，可按页面需要隐藏顶部导航区。 */
export function ModulePageFrame({
  title,
  toolbar,
  lastUpdated,
  main,
  side,
  contentLayoutClassName,
  showHeader = true,
}: ModulePageFrameProps) {
  const hasSide = side !== undefined && side !== null;
  return (
    <section className="space-y-6">
      {showHeader ? (
        <header className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-3xl">
              <h2 className="text-3xl font-semibold tracking-tight text-slate-950">{title}</h2>
            </div>
            {(toolbar || lastUpdated) && (
              <div className="flex flex-col gap-3 lg:items-end">
                {toolbar}
                {lastUpdated}
              </div>
            )}
          </div>
        </header>
      ) : null}

      <div className={contentLayoutClassName ?? "grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]"}>
        <div className="space-y-6">{main}</div>
        {hasSide ? <aside className="space-y-6">{side}</aside> : null}
      </div>
    </section>
  );
}
