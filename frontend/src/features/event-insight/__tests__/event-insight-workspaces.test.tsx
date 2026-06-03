import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EventGraphWorkspace } from "../components/event-graph-workspace";
import { TopicTraceWorkspace } from "../components/topic-trace-workspace";

describe("Event insight mock workspaces", () => {
  it("renders the topic trace metrics, current stage, and timeline", () => {
    render(<TopicTraceWorkspace />);

    expect(screen.getByRole("heading", { name: "主题溯源" })).toBeInTheDocument();
    expect(screen.getByText("阶段 03：HBM4 提前放量")).toBeInTheDocument();
    expect(screen.getByText("主题事件")).toBeInTheDocument();
    expect(screen.getByText("训练集群需求转向更高带宽内存配置")).toBeInTheDocument();
  });

  it("renders the relationship graph canvas and selected-node details", () => {
    render(<EventGraphWorkspace />);

    expect(screen.getByRole("heading", { name: "事件关系图" })).toBeInTheDocument();
    expect(screen.getByLabelText("事件关系图画布")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "节点详情" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "查看节点 数据中心液冷方案渗透率持续上升" }));

    expect(screen.getByRole("heading", { name: "数据中心液冷方案渗透率持续上升" })).toBeInTheDocument();
  });
});
