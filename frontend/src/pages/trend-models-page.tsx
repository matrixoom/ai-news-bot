import { ChartBarSquareIcon } from "@heroicons/react/24/outline";
import { ModulePageFrame } from "../shared/ui/module-page-frame";

export function TrendModelsPage() {
  return (
    <ModulePageFrame
      title="Trend Models"
      description="AI trend analysis and forecasting"
      lastUpdated={null}
      toolbar={null}
      main={
        <div className="workbench-panel flex min-h-72 flex-col items-center justify-center p-8 text-center">
          <div className="rounded-control bg-accent-soft p-3 text-accent">
            <ChartBarSquareIcon aria-hidden="true" className="h-7 w-7" />
          </div>
          <h2 className="mt-4 text-lg font-semibold text-ink">
            Trend Models
          </h2>
          <p className="mt-2 max-w-md text-sm leading-6 text-muted">
            趋势模型仍在定义阶段，当前仅统一呈现结构，不展示样例预测。
          </p>
        </div>
      }
    />
  );
}
