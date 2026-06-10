import { useEffect, useMemo, useState } from "react";

export type WorkbenchChartTheme = {
  dark: boolean;
  text: string;
  muted: string;
  line: string;
  splitLine: string;
  tooltipBackground: string;
  tooltipBorder: string;
  surface: string;
  accent: string;
  positive: string;
  negative: string;
};

/** 监听根节点主题属性，并返回统一的 ECharts 视觉令牌。 */
export function useWorkbenchChartTheme(): WorkbenchChartTheme {
  const [dark, setDark] = useState(() => document.documentElement.dataset.theme === "dark");

  useEffect(() => {
    const observer = new MutationObserver(() => {
      setDark(document.documentElement.dataset.theme === "dark");
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);

  return useMemo(
    () =>
      dark
        ? {
            dark,
            text: "#e2e8f0",
            muted: "#94a3b8",
            line: "#334155",
            splitLine: "#263449",
            tooltipBackground: "#0f172a",
            tooltipBorder: "#334155",
            surface: "#0f172a",
            accent: "#60a5fa",
            positive: "#f87171",
            negative: "#34d399",
          }
        : {
            dark,
            text: "#334155",
            muted: "#64748b",
            line: "#dfe5ec",
            splitLine: "#edf1f5",
            tooltipBackground: "#ffffff",
            tooltipBorder: "#dfe5ec",
            surface: "#ffffff",
            accent: "#2563eb",
            positive: "#dc2626",
            negative: "#059669",
          },
    [dark],
  );
}

/** 返回折线、柱状图共用的坐标轴与 tooltip 配置。 */
export function buildCartesianTheme(theme: WorkbenchChartTheme) {
  return {
    tooltip: {
      backgroundColor: theme.tooltipBackground,
      borderColor: theme.tooltipBorder,
      textStyle: { color: theme.text, fontSize: 12 },
    },
    legendText: { color: theme.muted, fontSize: 11 },
    categoryAxis: {
      axisLabel: { color: theme.muted, fontSize: 10 },
      axisLine: { lineStyle: { color: theme.line } },
      axisTick: { lineStyle: { color: theme.line } },
    },
    valueAxis: {
      axisLabel: { color: theme.muted, fontSize: 10 },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: theme.splitLine } },
      nameTextStyle: { color: theme.muted },
    },
  };
}
