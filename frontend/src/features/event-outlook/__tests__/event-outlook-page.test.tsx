import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

  function installTrackLayout(track: HTMLElement) {
    track.getBoundingClientRect = () =>
      ({
        x: 100,
        y: 100,
        left: 100,
        top: 100,
        right: 1100,
        bottom: 680,
        width: 1000,
        height: 580,
        toJSON: () => ({}),
      }) as DOMRect;
  }

  it("renders only the timeline canvas surface", async () => {
    installWorkbenchFetchMock();

    renderEventOutlookApp();

    expect(await screen.findByText("COMPUTEX 2026")).toBeInTheDocument();
    expect(await screen.findByText("夏季达沃斯 2026")).toBeInTheDocument();
    const canvas = screen.getByTestId("event-timeline-canvas");
    expect(within(canvas).getByRole("form", { name: "时间范围过滤器" })).toBeInTheDocument();
    expect(within(canvas).getByRole("button", { name: "新增事件" })).toBeInTheDocument();
    expect(screen.queryByText("Module workspace")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "国内" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "国际" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "天" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "周" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "月" })).not.toBeInTheDocument();
  });

  it("loads the international timeline from the route tab", async () => {
    const fetchMock = installWorkbenchFetchMock();

    renderEventOutlookApp("/event-outlook?tab=international");

    await waitFor(() => {
      expect(window.location.search).toContain("tab=international");
      expect(
        fetchMock.mock.calls.some(([input]) => String(input).includes("/api/frontend/modules/event-outlook?region=international")),
      ).toBe(true);
    });
    expect(await screen.findByText("Google I/O 2026")).toBeInTheDocument();
    expect(await screen.findByText("FOMC 利率会议")).toBeInTheDocument();
  });

  it("renders the event insight list without requesting the static calendar", async () => {
    const fetchMock = installWorkbenchFetchMock();

    renderEventOutlookApp("/event-outlook?tab=events");

    expect(await screen.findByRole("heading", { name: "事件列表" })).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(([input]) => String(input).includes("/api/frontend/modules/event-outlook")),
    ).toBe(false);
  });

  it("zooms into a dragged canvas range", async () => {
    const fetchMock = installWorkbenchFetchMock();

    renderEventOutlookApp("/event-outlook?tab=domestic&start_date=2026-05-05&end_date=2027-05-05");

    const track = await screen.findByTestId("event-timeline-track");
    installTrackLayout(track);
    fireEvent.mouseDown(track, { clientX: 300, clientY: 320, button: 0 });
    fireEvent.mouseMove(track, { clientX: 700, clientY: 320, buttons: 1 });
    fireEvent.mouseUp(track, { clientX: 700, clientY: 320 });

    await waitFor(() => {
      expect(window.location.search).toContain("start_date=2026-07-17");
      expect(window.location.search).toContain("end_date=2026-12-10");
      expect(
        fetchMock.mock.calls.some(([input]) => {
          const value = String(input);
          return value.includes("start_date=2026-07-17") && value.includes("end_date=2026-12-10");
        }),
      ).toBe(true);
    });
  });

  it("zooms with the mouse wheel around the cursor", async () => {
    const fetchMock = installWorkbenchFetchMock();

    renderEventOutlookApp("/event-outlook?tab=domestic&start_date=2026-05-05&end_date=2027-05-05");

    const track = await screen.findByTestId("event-timeline-track");
    installTrackLayout(track);
    fireEvent.wheel(track, { clientX: 600, deltaY: -120 });

    await waitFor(() => {
      expect(window.location.search).toContain("start_date=2026-06-10");
      expect(window.location.search).toContain("end_date=2027-03-29");
      expect(
        fetchMock.mock.calls.some(([input]) => {
          const value = String(input);
          return value.includes("start_date=2026-06-10") && value.includes("end_date=2027-03-29");
        }),
      ).toBe(true);
    });
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
