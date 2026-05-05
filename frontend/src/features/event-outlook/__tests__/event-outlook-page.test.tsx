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

  it("renders domestic and international timeline tabs with resolution controls", async () => {
    installWorkbenchFetchMock();

    renderEventOutlookApp();

    expect((await screen.findAllByRole("heading", { name: "Event Outlook" })).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "国内" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "国际" })).toBeInTheDocument();
    expect(await screen.findByText("COMPUTEX 2026")).toBeInTheDocument();
    expect(await screen.findByText("夏季达沃斯 2026")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "天" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "周" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "月" })).toBeInTheDocument();
    expect(screen.getByTestId("event-timeline-canvas")).toBeInTheDocument();
    expect(screen.getAllByText("Finance").length).toBeGreaterThan(0);
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

  it("applies a custom range and refreshes events", async () => {
    const fetchMock = installWorkbenchFetchMock();
    const user = userEvent.setup();

    renderEventOutlookApp();

    await user.clear(await screen.findByLabelText("起始日期"));
    await user.type(screen.getByLabelText("起始日期"), "2026-06-01");
    await user.clear(screen.getByLabelText("结束日期"));
    await user.type(screen.getByLabelText("结束日期"), "2026-12-31");
    await user.click(screen.getByRole("button", { name: "定位时间范围" }));
    await user.click(screen.getByRole("button", { name: "刷新" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input]) => {
          const value = String(input);
          return (
            value.includes("/api/frontend/modules/event-outlook") &&
            value.includes("start_date=2026-06-01") &&
            value.includes("end_date=2026-12-31") &&
            value.includes("refresh=1")
          );
        }),
      ).toBe(true);
    });
  });

  it("creates and edits timeline events through the persistence API", async () => {
    const fetchMock = installWorkbenchFetchMock();
    const user = userEvent.setup();

    renderEventOutlookApp();

    await user.type(await screen.findByLabelText("事件日期"), "2026-09-11");
    await user.type(screen.getByLabelText("事件标题"), "自定义发布会");
    await user.type(screen.getByLabelText("事件摘要"), "跟踪重点公司新品发布。");
    await user.click(screen.getByRole("button", { name: "保存事件" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input, init]) => {
          return String(input).endsWith("/api/frontend/modules/event-outlook/events") && (init as RequestInit)?.method === "POST";
        }),
      ).toBe(true);
    });

    const firstEvent = await screen.findByRole("button", { name: /编辑 COMPUTEX 2026/ });
    await user.click(firstEvent);
    const editPanel = screen.getByRole("form", { name: "编辑事件" });
    await user.clear(within(editPanel).getByLabelText("事件标题"));
    await user.type(within(editPanel).getByLabelText("事件标题"), "COMPUTEX 2026 更新");
    await user.clear(within(editPanel).getByLabelText("事件摘要"));
    await user.type(within(editPanel).getByLabelText("事件摘要"), "更新后的摘要。");
    await user.click(within(editPanel).getByRole("button", { name: "保存修改" }));

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
