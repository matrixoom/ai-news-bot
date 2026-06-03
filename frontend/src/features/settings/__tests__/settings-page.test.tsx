import { cleanup, fireEvent, render, screen } from "@testing-library/react";
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

  it("loads, tests, and saves llm settings without exposing plaintext keys", async () => {
    installWorkbenchFetchMock({ push: pushPayload });
    renderSettingsApp("/settings");

    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "大模型配置" })).toBeInTheDocument();
    expect(await screen.findByText("sk-...alue")).toBeInTheDocument();
    expect(screen.queryByText("sk-secret-value")).not.toBeInTheDocument();
    expect(screen.getByText("任务默认模型")).toBeInTheDocument();
    expect(screen.getByText("主题摘要")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "测试连接" }));
    expect(await screen.findByText("连接测试成功：主分析模型 / analysis-model 已返回响应。")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "新增配置" }));
    fireEvent.change(screen.getByLabelText("配置名称"), { target: { value: "快速抽取模型" } });
    fireEvent.change(screen.getByLabelText("Base URL"), { target: { value: "https://api.fast.example.com/v1" } });
    fireEvent.change(screen.getByLabelText("模型名称"), { target: { value: "fast-extract" } });
    fireEvent.change(screen.getByLabelText("API Key"), { target: { value: "sk-fast-secret" } });
    fireEvent.click(screen.getByRole("button", { name: "保存配置" }));

    expect(await screen.findByText("快速抽取模型")).toBeInTheDocument();
    expect(screen.queryByText("sk-fast-secret")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "编辑配置" }));
    fireEvent.change(screen.getByLabelText("模型名称"), { target: { value: "analysis-model-updated" } });
    fireEvent.click(screen.getByRole("button", { name: "保存配置" }));
    expect(await screen.findByText("analysis-model-updated")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "禁用配置" }));
    expect(await screen.findByText("模型配置已禁用。")).toBeInTheDocument();

    expect(screen.getByRole("heading", { name: "RSS 源配置" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "新增 RSS 源" }));
    fireEvent.change(screen.getByLabelText("RSS 名称"), { target: { value: "AI 财经观察" } });
    fireEvent.change(screen.getByLabelText("RSS URL"), { target: { value: "https://example.com/rss.xml" } });
    fireEvent.click(screen.getByRole("button", { name: "保存 RSS 源" }));
    expect(await screen.findByText("AI 财经观察")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "抓取 AI 财经观察" }));
    expect(await screen.findByText("抓取完成：1 条新增，0 条跳过。")).toBeInTheDocument();

    expect(screen.queryByText("Module workspace")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Workspace preferences" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Current defaults" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Default landing page")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save preferences" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Default news mode")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Show market ticker")).not.toBeInTheDocument();
  });
});
