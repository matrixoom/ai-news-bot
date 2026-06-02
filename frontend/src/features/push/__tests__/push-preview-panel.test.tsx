import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PushPreviewPanel } from "../components/push-preview-panel";

describe("PushPreviewPanel", () => {
  it("expands the iframe height to fit the rendered report content", async () => {
    render(
      <PushPreviewPanel
        preview={{
          ok: true,
          generatedAt: "2026-04-14T08:00:00Z",
          subject: "Market Daily",
          textBody: "",
          htmlBody: "<html><body><div style='height: 1600px;'>preview</div></body></html>",
          style: "newspaper",
          marketChartRange: "1y",
          selectedModuleIds: ["market"],
          error: "",
        }}
        refreshAfterMs={30000}
      />,
    );

    const iframe = screen.getByTitle("Push preview");
    Object.defineProperty(iframe, "contentDocument", {
      configurable: true,
      value: {
        body: { scrollHeight: 1580 },
        documentElement: { scrollHeight: 1624 },
      },
    });

    fireEvent.load(iframe);

    await waitFor(() => {
      expect(iframe).toHaveStyle({ height: "1648px" });
    });
  });

  it("opens a progress dialog while all market charts are being refreshed", async () => {
    const onRefreshCharts = vi.fn();
    const user = userEvent.setup();

    const { rerender } = render(
      <PushPreviewPanel
        onDismissChartRefresh={() => undefined}
        onRefreshCharts={onRefreshCharts}
        preview={{
          ok: true,
          generatedAt: "2026-04-14T08:00:00Z",
          subject: "Market Daily",
          textBody: "",
          htmlBody: "<html><body>preview</body></html>",
          style: "newspaper",
          marketChartRange: "1y",
          selectedModuleIds: ["market"],
          error: "",
        }}
        refreshAfterMs={30000}
      />,
    );

    await user.click(screen.getByRole("button", { name: "全量刷新图表" }));

    expect(onRefreshCharts).toHaveBeenCalledTimes(1);
    rerender(
      <PushPreviewPanel
        chartRefreshJob={{
          id: "job-1",
          status: "running",
          completed: 2,
          total: 6,
          percentage: 33,
          currentSymbol: "CSI500",
          currentLabel: "中证500",
          message: "正在刷新中证500。",
          errors: [],
        }}
        onDismissChartRefresh={() => undefined}
        onRefreshCharts={onRefreshCharts}
        preview={{
          ok: true,
          generatedAt: "2026-04-14T08:00:00Z",
          subject: "Market Daily",
          textBody: "",
          htmlBody: "<html><body>preview</body></html>",
          style: "newspaper",
          marketChartRange: "1y",
          selectedModuleIds: ["market"],
          error: "",
        }}
        refreshAfterMs={30000}
      />,
    );

    expect(screen.getByRole("dialog", { name: "宽基指数图表刷新进度" })).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "33");
    expect(screen.getByText("2 / 6")).toBeInTheDocument();
    expect(screen.getByText("正在刷新中证500。")).toBeInTheDocument();
  });

  it("renders compact accessible preview actions", () => {
    render(
      <PushPreviewPanel
        marketChartRange="1y"
        onMarketChartRangeChange={() => undefined}
        onOpenSettings={() => undefined}
        onPreview={() => undefined}
        onRefreshCharts={() => undefined}
        onSend={() => undefined}
        preview={{
          ok: true,
          generatedAt: "2026-04-14T08:00:00Z",
          subject: "Market Daily",
          textBody: "",
          htmlBody: "<html><body>preview</body></html>",
          style: "newspaper",
          marketChartRange: "1y",
          selectedModuleIds: ["market"],
          error: "",
        }}
        refreshAfterMs={30000}
      />,
    );

    expect(screen.getByLabelText("宽基指数时间范围")).toHaveValue("1y");
    for (const label of ["打开推送设置", "全量刷新图表", "刷新预览", "立即发送"]) {
      expect(screen.getByRole("button", { name: label })).toHaveAttribute("title", label);
    }
  });
});
