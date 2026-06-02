import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../../../app/app";
import {
  installWorkbenchFetchMock,
  marketPayload,
  pushPayload,
} from "../../../app/__tests__/workbench-api-mocks";

describe("PushPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  function renderPushApp(initialEntry = "/push?tab=schedules") {
    window.history.pushState({}, "", initialEntry);
    render(<App />);
  }

  function formatExpectedLocalTime(value: string): string {
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      timeZoneName: "short",
    }).format(new Date(value));
  }

  it("renders the schedules workspace as the first push tab", async () => {
    const fetchMock = installWorkbenchFetchMock({ push: pushPayload, market: marketPayload });
    const user = userEvent.setup();

    renderPushApp("/push?tab=schedules");

    expect(await screen.findByTitle("Push preview")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Delivery configuration" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Schedule editor" })).not.toBeInTheDocument();
    expect(screen.queryByText("Config path")).not.toBeInTheDocument();
    expect(screen.queryByText(/\.data[\\/]push_center\.json/)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Schedules" })).toHaveAttribute("aria-current", "page");
    expect(screen.queryByRole("link", { name: "Overview" })).not.toBeInTheDocument();
    expect(screen.getByTitle("Push preview")).toBeInTheDocument();
    expect(screen.queryByText("Text fallback")).not.toBeInTheDocument();

    expect(window.location.search).toContain("tab=schedules");
    expect(screen.getByTitle("Push preview")).toBeInTheDocument();
    expect(screen.queryByText("Manual runs and scheduled deliveries")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "打开推送设置" }));

    expect(screen.getByRole("dialog", { name: "推送设置" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Delivery configuration" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Schedule editor" })).toBeInTheDocument();
    expect(screen.getByLabelText("SMTP server")).toHaveValue("smtp.example.com");
    expect(screen.getByRole("button", { name: "Save configuration" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Refresh preview" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Send now" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "关闭推送设置" }));
    await user.click(screen.getByRole("link", { name: "History" }));

    expect(window.location.search).toContain("tab=history");
    expect(screen.getByRole("link", { name: "History" })).toHaveAttribute("aria-current", "page");
    expect(screen.queryByTitle("Push preview")).not.toBeInTheDocument();
    expect(screen.queryByText("Text fallback")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Run controls" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Send now" })).not.toBeInTheDocument();
    expect(screen.getByText("Market Daily")).toBeInTheDocument();

    expect(
      fetchMock.mock.calls
        .filter(([input]) => String(input).includes("/api/frontend/modules/push"))
        .every(([input]) => !String(input).includes("refresh=1")),
    ).toBe(true);
  });

  it("falls back to schedules when the old overview tab is requested", async () => {
    installWorkbenchFetchMock({ push: pushPayload, market: marketPayload });

    renderPushApp("/push?tab=overview");

    expect(await screen.findByTitle("Push preview")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Schedules" })).toHaveAttribute("aria-current", "page");
    expect(screen.queryByRole("link", { name: "Overview" })).not.toBeInTheDocument();
  });

  it("renders workspace and history timestamps in the browser local timezone", async () => {
    installWorkbenchFetchMock({ push: pushPayload, market: marketPayload });
    const user = userEvent.setup();

    renderPushApp("/push?tab=schedules");

    expect(await screen.findByText(formatExpectedLocalTime(String(pushPayload.generated_at)))).toBeInTheDocument();
    expect(screen.queryByText(/UTC/)).not.toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "History" }));

    expect(await screen.findByText(formatExpectedLocalTime("2026-03-30T08:00:00+08:00"))).toBeInTheDocument();
    expect(screen.queryByText("2026-03-30T08:00:00+08:00")).not.toBeInTheDocument();
  });

  it("saves configuration and refreshes preview from the current draft", async () => {
    const fetchMock = installWorkbenchFetchMock({ push: pushPayload, market: marketPayload });
    const user = userEvent.setup();

    renderPushApp("/push?tab=schedules");

    await user.click(await screen.findByRole("button", { name: "打开推送设置" }));
    const smtpServerInput = screen.getByLabelText("SMTP server");
    await user.clear(smtpServerInput);
    await user.type(smtpServerInput, "smtp.internal.example");
    await user.selectOptions(screen.getByLabelText("Report style"), "briefing");

    await user.click(screen.getByRole("button", { name: "Save configuration" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([input, init]) => String(input).includes("/api/push/config") && init?.method === "PUT",
        ),
      ).toBe(true);
    });
    expect(await screen.findByText(/Saved to/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "关闭推送设置" }));
    await user.click(screen.getByRole("button", { name: "刷新预览" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([input, init]) => String(input).includes("/api/push/preview") && init?.method === "POST",
        ),
      ).toBe(true);
    });
    expect(await screen.findByText("Preview refreshed.")).toBeInTheDocument();
    expect(screen.getByText("Preview for briefing")).toBeInTheDocument();
  });

  it("keeps unsaved settings draft when the dialog closes and reopens", async () => {
    installWorkbenchFetchMock({ push: pushPayload, market: marketPayload });
    const user = userEvent.setup();

    renderPushApp("/push?tab=schedules");

    await user.click(await screen.findByRole("button", { name: "打开推送设置" }));
    const smtpServerInput = screen.getByLabelText("SMTP server");
    await user.clear(smtpServerInput);
    await user.type(smtpServerInput, "smtp.unsaved.example");
    await user.click(screen.getByRole("button", { name: "关闭推送设置" }));
    await user.click(screen.getByRole("button", { name: "打开推送设置" }));

    expect(screen.getByLabelText("SMTP server")).toHaveValue("smtp.unsaved.example");
  });

  it("refreshes all market charts with progress and redraws the preview", async () => {
    const fetchMock = installWorkbenchFetchMock({ push: pushPayload, market: marketPayload });
    const user = userEvent.setup();

    renderPushApp("/push?tab=schedules");

    await user.click(await screen.findByRole("button", { name: "全量刷新图表" }));

    expect(await screen.findByRole("dialog", { name: "宽基指数图表刷新进度" })).toBeInTheDocument();
    expect(screen.getByText("正在刷新 中证500。")).toBeInTheDocument();

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([input, init]) => String(input).includes("/api/push/market-chart-refresh") && init?.method === "POST",
        ),
      ).toBe(true);
      expect(
        fetchMock.mock.calls.some(
          ([input, init]) => String(input).includes("/api/push/market-chart-refresh/market-chart-refresh-1")
            && (init?.method ?? "GET") === "GET",
        ),
      ).toBe(true);
    });
    const requestCall = fetchMock.mock.calls.find(
      ([input, init]) => String(input).includes("/api/push/market-chart-refresh") && init?.method === "POST",
    );
    expect(JSON.parse(String(requestCall?.[1]?.body))).toMatchObject({
      config: { market_chart_range: "1y" },
    });
    expect(await screen.findByText("Charts refreshed")).toBeInTheDocument();
  });

  it("redraws the preview locally when the market chart range changes", async () => {
    const fetchMock = installWorkbenchFetchMock({ push: pushPayload, market: marketPayload });
    const user = userEvent.setup();
    renderPushApp("/push?tab=schedules");

    await user.selectOptions(await screen.findByLabelText("宽基指数时间范围"), "2y");

    await waitFor(() => {
      const previewCall = fetchMock.mock.calls.find(
        ([input, init]) => String(input).includes("/api/push/preview") && init?.method === "POST",
      );
      expect(JSON.parse(String(previewCall?.[1]?.body))).toMatchObject({
        config: { market_chart_range: "2y" },
        refresh_data: false,
      });
    });
  });

  it("triggers a manual push from the schedules controls", async () => {
    const fetchMock = installWorkbenchFetchMock({ push: pushPayload, market: marketPayload });
    const user = userEvent.setup();

    renderPushApp("/push?tab=schedules");

    await user.click(await screen.findByRole("button", { name: "立即发送" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([input, init]) => String(input).includes("/api/push/trigger") && init?.method === "POST",
        ),
      ).toBe(true);
    });
    const requestCall = fetchMock.mock.calls.find(
      ([input, init]) => String(input).includes("/api/push/trigger") && init?.method === "POST",
    );
    expect(JSON.parse(String(requestCall?.[1]?.body))).toMatchObject({
      config: { market_chart_range: "1y" },
    });

    expect(await screen.findByText("Manual push sent.")).toBeInTheDocument();
  });
});
