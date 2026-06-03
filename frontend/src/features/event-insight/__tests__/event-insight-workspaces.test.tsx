import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EventGraphWorkspace } from "../components/event-graph-workspace";
import { TopicTraceWorkspace } from "../components/topic-trace-workspace";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Event insight mock workspaces", () => {
  it("loads topic trace metrics, current stage, and timeline from API", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(eventInsightFetch);

    renderWithQueryClient(<TopicTraceWorkspace />);

    expect(screen.getByRole("heading", { name: "主题溯源" })).toBeInTheDocument();
    expect(await screen.findByText("阶段 02：CPO 光模块订单增加")).toBeInTheDocument();
    expect(screen.getByText("主题事件")).toBeInTheDocument();
    expect(screen.getAllByText("存储芯片报价上调").length).toBeGreaterThan(0);
    expect(screen.getAllByText("DRAM 合约价上涨，AI 服务器需求支撑内存涨价。").length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/api/frontend/modules/event-insight/topics/7/trace"), expect.any(Object));
  });

  it("shows topic trace loading state", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise(() => undefined));

    renderWithQueryClient(<TopicTraceWorkspace />);

    expect(screen.getByText("正在加载主题溯源...")).toBeInTheDocument();
  });

  it("renders the relationship graph canvas and selected-node details", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(eventInsightFetch);

    renderWithQueryClient(<EventGraphWorkspace />);

    expect(screen.getByRole("heading", { name: "事件关系图" })).toBeInTheDocument();
    expect(await screen.findByLabelText("事件关系图画布")).toBeInTheDocument();
    expect(screen.getByText("内存涨价推升光模块订单预期。")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "查看节点 数据中心液冷方案渗透率持续上升" }));

    expect(screen.getByRole("heading", { name: "数据中心液冷方案渗透率持续上升" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/api/frontend/modules/event-insight/graph?topicId=7"), expect.any(Object));
  });

  it("shows event graph loading state", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise(() => undefined));

    renderWithQueryClient(<EventGraphWorkspace />);

    expect(screen.getByText("正在加载事件关系图...")).toBeInTheDocument();
  });

  it("creates topics and graph relations from toolbar buttons", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(eventInsightFetch);

    renderWithQueryClient(<TopicTraceWorkspace />);

    expect(await screen.findByText("主题事件")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "新建主题" }));
    fireEvent.change(screen.getByLabelText("主题名称"), { target: { value: "商业航天" } });
    fireEvent.click(screen.getByRole("button", { name: "保存主题" }));
    expect(await screen.findByText("主题已创建：商业航天")).toBeInTheDocument();

    renderWithQueryClient(<EventGraphWorkspace />);

    expect(await screen.findByLabelText("事件关系图画布")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "新增关系" }));
    fireEvent.change(screen.getByLabelText("关系说明"), { target: { value: "订单变化验证涨价链条。" } });
    fireEvent.click(screen.getByRole("button", { name: "保存关系" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/frontend/modules/event-insight/relations", expect.objectContaining({ method: "POST" })));

    fireEvent.click(screen.getByRole("button", { name: "保存视图" }));
    expect(await screen.findByText("视图已保存到当前工作区。")).toBeInTheDocument();
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

const topicsPayload = {
  traceId: "event-insight-topics-test",
  items: [{ id: 7, name: "内存涨价", summary: "围绕存储芯片供需变化。", lifecycleStage: "tracking", heatScore: 0.72 }],
  total: 1,
};

const eventGraphPayload = {
  traceId: "event-insight-graph-test",
  nodes: [
    {
      id: "event-1",
      eventId: 1,
      kind: "price_change",
      title: "存储芯片报价上调",
      happenedAt: "2026-05-16T10:30:00+08:00",
      confidence: "高可信 · 82",
      confidenceTone: "green",
      summary: "DRAM 合约价上涨，AI 服务器需求支撑内存涨价。",
      left: "12%",
      top: "22%",
    },
    {
      id: "event-2",
      eventId: 2,
      kind: "supply_demand",
      title: "数据中心液冷方案渗透率持续上升",
      happenedAt: "2026-05-20T10:30:00+08:00",
      confidence: "中可信 · 76",
      confidenceTone: "amber",
      summary: "海外云厂商资本开支上修。",
      left: "58%",
      top: "46%",
    },
  ],
  edges: [
    {
      id: "relation-1",
      sourceNodeId: "event-1",
      targetNodeId: "event-2",
      type: "cause",
      summary: "内存涨价推升光模块订单预期。",
      left: "25%",
      top: "35%",
      width: "34%",
      rotate: "18deg",
    },
  ],
  selectedNodeId: "event-1",
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

async function eventInsightFetch(input: RequestInfo | URL, init?: RequestInit) {
  const url = resolveRequestUrl(input);
  const method = init?.method ?? (input instanceof Request ? input.method : "GET");
  if (url.pathname === "/api/frontend/modules/event-insight/topics") {
    if (method === "POST") {
      return jsonResponse({ traceId: "topic-create", topic: { id: 9, name: "商业航天", summary: "" } });
    }
    return jsonResponse(topicsPayload);
  }
  if (url.pathname === "/api/frontend/modules/event-insight/topics/7/trace") {
    return jsonResponse(topicTracePayload);
  }
  if (url.pathname === "/api/frontend/modules/event-insight/graph") {
    return jsonResponse(eventGraphPayload);
  }
  if (url.pathname === "/api/frontend/modules/event-insight/relations") {
    return jsonResponse({ traceId: "relation-create", relation: { id: 3 } });
  }
  throw new Error(`Unexpected request ${url.pathname}${url.search}`);
}

function resolveRequestUrl(input: RequestInfo | URL) {
  if (typeof input === "string") {
    return new URL(input, window.location.origin);
  }
  if (input instanceof URL) {
    return input;
  }
  return new URL(input.url, window.location.origin);
}
