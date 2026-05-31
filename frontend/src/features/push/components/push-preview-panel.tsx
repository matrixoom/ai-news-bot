import { ArrowPathIcon, XMarkIcon } from "@heroicons/react/24/outline";
import { useEffect, useRef, useState } from "react";
import type { PushMarketChartRefreshJob, PushPreview } from "../model/push-module.types";

type PushPreviewPanelProps = {
  preview: PushPreview;
  refreshAfterMs: number;
  chartRefreshJob?: PushMarketChartRefreshJob | null;
  onDismissChartRefresh?: () => void;
  onRefreshCharts?: () => void;
};

export function PushPreviewPanel({
  preview,
  refreshAfterMs,
  chartRefreshJob = null,
  onDismissChartRefresh,
  onRefreshCharts,
}: PushPreviewPanelProps) {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const [frameHeight, setFrameHeight] = useState(960);
  const isChartRefreshing = chartRefreshJob?.status === "pending" || chartRefreshJob?.status === "running";

  useEffect(() => {
    setFrameHeight(960);
  }, [preview.htmlBody, preview.ok]);

  function resizePreviewFrame() {
    const iframe = iframeRef.current;
    const documentNode = iframe?.contentDocument ?? iframe?.contentWindow?.document;
    if (!documentNode) {
      return;
    }
    const contentHeight = Math.max(
      documentNode.body?.scrollHeight ?? 0,
      documentNode.documentElement?.scrollHeight ?? 0,
    );
    if (contentHeight <= 0) {
      return;
    }
    setFrameHeight(Math.max(960, contentHeight + 24));
  }

  return (
    <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Preview</p>
          <h3 className="mt-2 text-lg font-semibold text-slate-950">Push preview</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Refresh interval {Math.round(refreshAfterMs / 1000)}s, rendered from the current draft.
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          {onRefreshCharts ? (
            <button
              className="inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:border-slate-400 hover:text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isChartRefreshing}
              onClick={onRefreshCharts}
              type="button"
            >
              <ArrowPathIcon aria-hidden="true" className={["h-4 w-4", isChartRefreshing ? "animate-spin" : ""].join(" ")} />
              全量刷新图表
            </button>
          ) : null}
          <span
            className={[
              "rounded-full border px-3 py-1 text-xs font-medium",
              preview.ok
                ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                : "border-rose-200 bg-rose-50 text-rose-700",
            ].join(" ")}
          >
            {preview.ok ? "Ready" : "Problem"}
          </span>
        </div>
      </div>

      <div className="mt-5 space-y-3">
        <p className="text-sm font-medium text-slate-500">Subject</p>
        <p className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-950">
          {preview.subject || "Preview subject unavailable"}
        </p>
      </div>

      {preview.ok ? (
        <div className="mt-5">
          <iframe
            aria-label="Push preview HTML"
            className="w-full rounded-2xl border border-slate-200 bg-white"
            onLoad={resizePreviewFrame}
            ref={iframeRef}
            sandbox="allow-same-origin"
            srcDoc={preview.htmlBody || "<p style='font-family: sans-serif;'>No HTML preview available.</p>"}
            style={{ height: `${frameHeight}px` }}
            title="Push preview"
          />
        </div>
      ) : (
        <div className="mt-5 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          <p className="font-medium">Preview unavailable</p>
          <p className="mt-2">{preview.error || "The backend could not build a preview."}</p>
        </div>
      )}

      {chartRefreshJob ? (
        <MarketChartRefreshDialog
          job={chartRefreshJob}
          onDismiss={onDismissChartRefresh}
        />
      ) : null}
    </section>
  );
}

function MarketChartRefreshDialog({
  job,
  onDismiss,
}: {
  job: PushMarketChartRefreshJob;
  onDismiss?: () => void;
}) {
  const canDismiss = job.status !== "pending" && job.status !== "running";
  const hasWarnings = job.status === "completed_with_warnings" || job.status === "failed";

  return (
    <div
      aria-labelledby="market-chart-refresh-title"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4"
      role="dialog"
    >
      <div className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Market charts</p>
            <h4 className="mt-2 text-lg font-semibold text-slate-950" id="market-chart-refresh-title">
              宽基指数图表刷新进度
            </h4>
          </div>
          {canDismiss && onDismiss ? (
            <button
              aria-label="关闭刷新进度"
              className="rounded-full border border-slate-200 p-2 text-slate-500 transition hover:text-slate-950"
              onClick={onDismiss}
              type="button"
            >
              <XMarkIcon aria-hidden="true" className="h-4 w-4" />
            </button>
          ) : null}
        </div>

        <div className="mt-6">
          <div className="flex items-center justify-between text-sm font-medium text-slate-700">
            <span>{job.currentLabel || "准备刷新"}</span>
            <span>{job.completed} / {job.total}</span>
          </div>
          <div
            aria-valuemax={100}
            aria-valuemin={0}
            aria-valuenow={job.percentage}
            className="mt-3 h-3 overflow-hidden rounded-full bg-slate-100"
            role="progressbar"
          >
            <div
              className={[
                "h-full rounded-full transition-all duration-300",
                hasWarnings ? "bg-amber-500" : "bg-sky-600",
              ].join(" ")}
              style={{ width: `${job.percentage}%` }}
            />
          </div>
          <p className="mt-4 text-sm leading-6 text-slate-600">{job.message}</p>
        </div>

        {job.errors.length > 0 ? (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4">
            <p className="text-sm font-semibold text-amber-900">部分指数保留上次可用历史</p>
            <ul className="mt-2 space-y-1 text-sm leading-6 text-amber-800">
              {job.errors.map((error) => <li key={error}>{error}</li>)}
            </ul>
          </div>
        ) : null}
      </div>
    </div>
  );
}
