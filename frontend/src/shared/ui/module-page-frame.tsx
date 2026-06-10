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
  description,
  toolbar,
  lastUpdated,
  main,
  side,
  contentLayoutClassName,
  showHeader = true,
}: ModulePageFrameProps) {
  const hasSide = side !== undefined && side !== null;
  return (
    <section className="space-y-4">
      {showHeader ? (
        <header className="border-b border-line pb-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-3xl">
              <h2 className="text-2xl font-semibold tracking-tight text-ink">{title}</h2>
              <p className="mt-1 text-sm leading-6 text-muted">{description}</p>
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

      <div className={contentLayoutClassName ?? "grid gap-4 xl:grid-cols-[minmax(0,1fr)_300px]"}>
        <div className="space-y-4">{main}</div>
        {hasSide ? <aside className="space-y-4">{side}</aside> : null}
      </div>
    </section>
  );
}
