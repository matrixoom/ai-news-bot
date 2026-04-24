import { useEffect, useRef, useState } from "react";
import type { PushPreview } from "../model/push-module.types";

type PushPreviewPanelProps = {
  preview: PushPreview;
  refreshAfterMs: number;
};

export function PushPreviewPanel({ preview, refreshAfterMs }: PushPreviewPanelProps) {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const [frameHeight, setFrameHeight] = useState(960);

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
    </section>
  );
}
