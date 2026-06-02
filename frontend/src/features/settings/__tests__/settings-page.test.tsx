import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../../../app/app";
import { installWorkbenchFetchMock, pushPayload } from "../../../app/__tests__/workbench-api-mocks";

describe("SettingsPage", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  function renderSettingsApp(initialEntry = "/settings") {
    window.history.pushState({}, "", initialEntry);
    render(<App />);
  }

  it("renders the display-only llm settings workspace", async () => {
    installWorkbenchFetchMock({ push: pushPayload });
    renderSettingsApp("/settings");

    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "大模型配置" })).toBeInTheDocument();
    expect(screen.getAllByText("主分析模型").length).toBeGreaterThan(0);
    expect(screen.getByText("任务默认模型")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "测试连接" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "保存配置" })).toBeDisabled();
    expect(screen.queryByText("Module workspace")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Workspace preferences" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Current defaults" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Default landing page")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save preferences" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Default news mode")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Show market ticker")).not.toBeInTheDocument();
  });
});
