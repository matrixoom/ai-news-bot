import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EventGraphWorkspace } from "../components/event-graph-workspace";
import { TopicTraceWorkspace } from "../components/topic-trace-workspace";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Event insight mock workspaces", () => {
  it("loads topic trace metrics, current stage, and timeline from API", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(topicTracePayload));

    renderWithQueryClient(<TopicTraceWorkspace />);

    expect(screen.getByRole("heading", { name: "主题溯源" })).toBeInTheDocument();
    expect(await screen.findByText("阶段 02：CPO 光模块订单增加")).toBeInTheDocument();
    expect(screen.getByText("主题事件")).toBeInTheDocument();
    expect(screen.getAllByText("存储芯片报价上调").length).toBeGreaterThan(0);
    expect(screen.getAllByText("DRAM 合约价上涨，AI 服务器需求支撑内存涨价。").length).toBeGreaterThan(0);
  });

  it("shows topic trace loading state", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise(() => undefined));

    renderWithQueryClient(<TopicTraceWorkspace />);

    expect(screen.getByText("正在加载主题溯源...")).toBeInTheDocument();
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

const topicTracePayload = {
  traceId: "event-insight-topic-trace-test",
  topic: {
    id: 1,
    name: "内存涨价",
    summary: "围绕存储芯片供需变化。",
    lifecycleStage: "tracking",
    heatScore: 0.72,
  },
  metrics: [
    { label: "主题事件", value: "2", note: "按时间倒序展示", noteTone: "green" },
    { label: "有效证据", value: "1", note: "覆盖 1 份材料", noteTone: "green" },
    { label: "关键节点", value: "2", note: "由关联事件生成", noteTone: "green" },
    { label: "待验证线索", value: "0", note: "暂无待验证线索", noteTone: "amber" },
  ],
  stages: [
    { id: "stage-1", label: "阶段 01", title: "存储芯片报价上调", active: false },
    { id: "stage-2", label: "阶段 02 · 当前", title: "CPO 光模块订单增加", active: true },
  ],
  timeline: [
    {
      id: "event-2",
      eventId: 2,
      happenedAt: "2026-05-20T10:30:00+08:00",
      title: "CPO 光模块订单增加",
      summary: "海外云厂商资本开支上修。",
      roleInTopic: "supporting_event",
      evidenceCount: 0,
      evidence: [],
    },
    {
      id: "event-1",
      eventId: 1,
      happenedAt: "2026-05-16T10:30:00+08:00",
      title: "存储芯片报价上调",
      summary: "DRAM 合约价上涨，AI 服务器需求支撑内存涨价。",
      roleInTopic: "key_catalyst",
      evidenceCount: 1,
      evidence: [{ id: 1, excerpt: "DRAM 合约价上涨，AI 服务器需求支撑内存涨价。", sourceTitle: "存储芯片报价上调" }],
    },
  ],
  currentJudgement: {
    title: "阶段 02：CPO 光模块订单增加",
    summary: "海外云厂商资本开支上修。",
    clues: ["继续补充交叉证据"],
  },
};

function renderWithQueryClient(children: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(<QueryWrapper queryClient={queryClient}>{children}</QueryWrapper>);
}

function QueryWrapper({ children, queryClient }: PropsWithChildren<{ queryClient: QueryClient }>) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
