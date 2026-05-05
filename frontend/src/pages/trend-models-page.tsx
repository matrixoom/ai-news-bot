import { ModulePageFrame } from "../shared/ui/module-page-frame";

export function TrendModelsPage() {
  return (
    <ModulePageFrame
      title="Trend Models"
      description="AI trend analysis and forecasting"
      lastUpdated={null}
      toolbar={null}
      main={
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="rounded-full bg-slate-100 p-6">
            <svg
              className="h-12 w-12 text-slate-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605"
              />
            </svg>
          </div>
          <h2 className="mt-6 text-xl font-semibold text-slate-700">
            Trend Models
          </h2>
          <p className="mt-2 max-w-md text-sm text-slate-500">
            AI 驱动的趋势分析和预测模型即将上线，敬请期待。
          </p>
        </div>
      }
    />
  );
}
