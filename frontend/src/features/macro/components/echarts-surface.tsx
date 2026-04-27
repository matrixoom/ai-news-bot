import { useEffect, useRef, type ReactNode } from "react";
import { BarChart, LineChart } from "echarts/charts";
import { DataZoomComponent, GridComponent, LegendComponent, MarkLineComponent, TooltipComponent } from "echarts/components";
import { init, use, type EChartsType } from "echarts/core";
import type { EChartsOption } from "echarts";
import { SVGRenderer } from "echarts/renderers";

use([LineChart, BarChart, GridComponent, LegendComponent, TooltipComponent, DataZoomComponent, MarkLineComponent, SVGRenderer]);

type EChartsSurfaceProps = {
  ariaLabel: string;
  title: string;
  description: string;
  option?: EChartsOption;
  height?: number;
  footer?: ReactNode;
};

/**
 * 渲染宏观页图表容器，并在窗口尺寸变化时同步重绘。
 * @param props 图表区域标题、说明、配置与辅助信息。
 * @returns 可访问的图表区域。
 */
export function EChartsSurface({ ariaLabel, title, description, option, height = 320, footer }: EChartsSurfaceProps) {
  const chartRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const element = chartRef.current;
    const isJsdom = typeof window !== "undefined" && /jsdom/i.test(window.navigator.userAgent);

    if (!element || !option || isJsdom) {
      return;
    }

    let chart: EChartsType | null = null;
    let frameId = 0;
    let resizeObserver: ResizeObserver | null = null;

    /**
     * 以当前容器尺寸初始化图表，避免在测试环境里依赖真实布局。
     */
    const mountChart = () => {
      const width = element.clientWidth || 960;
      const resolvedHeight = element.clientHeight || height;

      chart = init(element, undefined, {
        renderer: "svg",
        width,
        height: resolvedHeight,
      });
      chart.setOption(option);
    };

    /**
     * 在容器尺寸变化时同步刷新图表尺寸。
     */
    const handleResize = () => {
      if (!chart) {
        mountChart();
        return;
      }

      chart.resize({
        width: element.clientWidth || 960,
        height: element.clientHeight || height,
      });
    };

    frameId = window.requestAnimationFrame(() => {
      mountChart();
    });

    if (typeof ResizeObserver !== "undefined") {
      resizeObserver = new ResizeObserver(() => {
        handleResize();
      });
      resizeObserver.observe(element);
    }

    window.addEventListener("resize", handleResize);

    return () => {
      window.cancelAnimationFrame(frameId);
      resizeObserver?.disconnect();
      window.removeEventListener("resize", handleResize);
      chart?.dispose();
    };
  }, [height, option]);

  return (
    <section aria-label={ariaLabel} className="rounded-[1.5rem] border border-slate-200 bg-slate-50/70 p-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="max-w-2xl">
          <h4 className="text-base font-semibold text-slate-950">{title}</h4>
          <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p>
        </div>
      </div>

      {option ? (
        <div
          ref={chartRef}
          className="mt-4 w-full rounded-2xl bg-white"
          style={{ height }}
        />
      ) : (
        <div className="mt-4 rounded-2xl border border-dashed border-slate-300 bg-white px-4 py-6 text-sm text-slate-500">
          暂无可绘制的历史数据。
        </div>
      )}

      {footer ? <div className="mt-4">{footer}</div> : null}
    </section>
  );
}
