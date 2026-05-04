import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import * as echarts from "echarts";
import { XMarkIcon } from "@heroicons/react/24/outline";

type ChartFullscreenProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  option: echarts.EChartsOption | null;
};

export function ChartFullscreen({ open, onClose, title, option }: ChartFullscreenProps) {
  const chartRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open || !option || !chartRef.current) return;

    const instance = echarts.init(chartRef.current, undefined, { renderer: "svg" });
    instance.setOption({ ...option, animation: false });

    const handleResize = () => instance.resize();
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      instance.dispose();
    };
  }, [open, option]);

  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-6"
      onClick={onClose}
    >
      <div
        className="relative flex h-[85vh] w-[90vw] flex-col rounded-2xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-slate-950">{title}</h2>
          <button
            type="button"
            className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 hover:bg-slate-100"
            onClick={onClose}
            aria-label="关闭全屏"
          >
            <XMarkIcon aria-hidden="true" className="h-5 w-5" />
          </button>
        </div>
        <div className="flex-1 p-4">
          <div ref={chartRef} className="h-full w-full" />
        </div>
      </div>
    </div>,
    document.body,
  );
}
