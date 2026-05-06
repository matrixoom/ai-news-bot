import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../../../app/app";
import { installWorkbenchFetchMock } from "../../../app/__tests__/workbench-api-mocks";

describe("EventOutlookPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  function renderEventOutlookApp(initialEntry = "/event-outlook?tab=domestic") {
    window.history.pushState({}, "", initialEntry);
    render(<App />);
  }

  it("renders domestic and international tabs with one timeline canvas", async () => {
    installWorkbenchFetchMock();

    renderEventOutlookApp();

    expect((await screen.findAllByRole("heading", { name: "Event Outlook" })).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "国内" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "国际" })).toBeInTheDocument();
    expect(await screen.findByText("COMPUTEX 2026")).toBeInTheDocument();
    expect(await screen.findByText("夏季达沃斯 2026")).toBeInTheDocument();
    const canvas = screen.getByTestId("event-timeline-canvas");
    expect(within(canvas).getByRole("form", { name: "时间范围过滤器" })).toBeInTheDocument();
    expect(within(canvas).getByRole("button", { name: "新增事件" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "天" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "周" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "月" })).not.toBeInTheDocument();
  });

  it("switches to the international timeline tab", async () => {
    const fetchMock = installWorkbenchFetchMock();
    const user = userEvent.setup();

    renderEventOutlookApp();

    await user.click(await screen.findByRole("link", { name: "国际" }));

    await waitFor(() => {
      expect(window.location.search).toContain("tab=international");
      expect(
        fetchMock.mock.calls.some(([input]) => String(input).includes("/api/frontend/modules/event-outlook?region=international")),
      ).toBe(true);
    });
    expect(await screen.findByText("Google I/O 2026")).toBeInTheDocument();
    expect(await screen.findByText("FOMC 利率会议")).toBeInTheDocument();
  });

  it("applies a custom range from the canvas filter", async () => {
    const fetchMock = installWorkbenchFetchMock();
    const user = userEvent.setup();

    renderEventOutlookApp();

    const canvas = await screen.findByTestId("event-timeline-canvas");
    await user.clear(within(canvas).getByLabelText("起始日期"));
    await user.type(within(canvas).getByLabelText("起始日期"), "2026-06-01");
    await user.clear(within(canvas).getByLabelText("结束日期"));
    await user.type(within(canvas).getByLabelText("结束日期"), "2026-12-31");
    await user.click(within(canvas).getByRole("button", { name: "筛选" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input]) => {
          const value = String(input);
          return (
            value.includes("/api/frontend/modules/event-outlook") &&
            value.includes("start_date=2026-06-01") &&
            value.includes("end_date=2026-12-31")
          );
        }),
      ).toBe(true);
    });
  });

  it("creates and edits timeline events from canvas dialogs", async () => {
    const fetchMock = installWorkbenchFetchMock();
    const user = userEvent.setup();

    renderEventOutlookApp();

    const canvas = await screen.findByTestId("event-timeline-canvas");
    await user.click(within(canvas).getByRole("button", { name: "新增事件" }));
    const createDialog = screen.getByRole("dialog", { name: "新增时间轴事件" });
    await user.type(within(createDialog).getByLabelText("事件日期"), "2026-09-11");
    await user.type(within(createDialog).getByLabelText("事件标题"), "自定义发布会");
    await user.type(within(createDialog).getByLabelText("事件摘要"), "跟踪重点公司新品发布。");
    await user.click(within(createDialog).getByRole("button", { name: "保存事件" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input, init]) => {
          return String(input).endsWith("/api/frontend/modules/event-outlook/events") && (init as RequestInit)?.method === "POST";
        }),
      ).toBe(true);
    });

    const firstEvent = await within(canvas).findByRole("button", { name: /编辑 COMPUTEX 2026/ });
    await user.click(firstEvent);
    const editDialog = screen.getByRole("dialog", { name: "编辑时间轴事件" });
    await user.clear(within(editDialog).getByLabelText("事件标题"));
    await user.type(within(editDialog).getByLabelText("事件标题"), "COMPUTEX 2026 更新");
    await user.clear(within(editDialog).getByLabelText("事件摘要"));
    await user.type(within(editDialog).getByLabelText("事件摘要"), "更新后的摘要。");
    await user.click(within(editDialog).getByRole("button", { name: "保存修改" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input, init]) => {
          return (
            String(input).includes("/api/frontend/modules/event-outlook/events/") &&
            (init as RequestInit)?.method === "PUT"
          );
        }),
      ).toBe(true);
    });
  });
});
