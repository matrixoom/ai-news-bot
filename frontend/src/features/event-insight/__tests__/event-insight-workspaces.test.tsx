import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { PropsWithChildren, ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EventGraphWorkspace } from "../components/event-graph-workspace";
import { TopicTraceWorkspace } from "../components/topic-trace-workspace";

vi.mock("@xyflow/react", async () => {
  const React = await import("react");

  type MockFlowNode = {
    data: Record<string, unknown>;
    draggable?: boolean;
    id: string;
    selected?: boolean;
    type?: string;
  };

  type MockFlowEdge = {
    data: Record<string, unknown>;
    id: string;
    type?: string;
  };

  return {
    Background: () => <div data-testid="react-flow-background" />,
    BackgroundVariant: { Dots: "dots" },
    BaseEdge: ({ path }: { path: string }) => <path d={path} data-testid="react-flow-base-edge" />,
    Controls: () => <div data-testid="react-flow-controls" />,
    EdgeLabelRenderer: ({ children }: { children: ReactNode }) => <g data-testid="react-flow-edge-labels">{children}</g>,
    Handle: () => <span data-testid="react-flow-handle" />,
    MarkerType: { ArrowClosed: "arrowclosed" },
    Position: { Bottom: "bottom", Left: "left", Right: "right", Top: "top" },
    ReactFlowProvider: ({ children }: { children: ReactNode }) => <div data-testid="react-flow-provider">{children}</div>,
    getBezierPath: () => ["M 0 0 Q 60 20 120 40", 60, 20],
    useEdgesState: (initialEdges: MockFlowEdge[]) => {
      const [edges, setEdges] = React.useState(initialEdges);
      return [edges, setEdges, vi.fn()];
    },
    useNodesState: (initialNodes: MockFlowNode[]) => {
      const [nodes, setNodes] = React.useState(initialNodes);
      return [nodes, setNodes, vi.fn()];
    },
    useReactFlow: () => ({ fitView: vi.fn() }),
    ReactFlow: ({
      children,
      edges,
      edgeTypes,
      nodes,
      nodeTypes,
    }: {
      children: ReactNode;
      edges: MockFlowEdge[];
      edgeTypes: Record<string, React.ComponentType<Record<string, unknown>>>;
      nodes: MockFlowNode[];
      nodeTypes: Record<string, React.ComponentType<Record<string, unknown>>>;
    }) => (
      <div aria-label="关系网络画布" data-testid="react-flow-canvas">
        {nodes.map((node) => {
          const NodeComponent = nodeTypes[node.type ?? "eventNode"];
          return (
            <div data-draggable={String(node.draggable !== false)} data-testid={`rf-node-${node.id}`} key={node.id}>
              <NodeComponent data={node.data} id={node.id} selected={node.selected ?? false} />
            </div>
          );
        })}
        <svg>
          {edges.map((edge) => {
            const EdgeComponent = edgeTypes[edge.type ?? "eventEdge"];
            return <EdgeComponent data={edge.data} id={edge.id} key={edge.id} sourceX={0} sourceY={0} targetX={120} targetY={40} />;
          })}
        </svg>
        {children}
      </div>
    ),
  };
});

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

  it("renders a React Flow relationship canvas without side panels or entity legend", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(eventInsightFetch);

    renderWithQueryClient(<EventGraphWorkspace />);

    expect(screen.getByRole("heading", { name: "关系网络" })).toBeInTheDocument();
    expect(await screen.findByLabelText("关系网络画布")).toBeInTheDocument();
    expect(screen.getByTestId("react-flow-canvas")).toBeInTheDocument();
    expect(screen.getByTestId("react-flow-background")).toBeInTheDocument();
    expect(screen.getByTestId("react-flow-controls")).toBeInTheDocument();
    expect(await screen.findByText("内存涨价推升光模块订单预期。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "刷新关系网络" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "全屏画布" })).toBeInTheDocument();
    expect(screen.queryByText("关系类型")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "节点详情" })).not.toBeInTheDocument();
    expect(screen.queryByText("Entity Types")).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/frontend/modules/event-insight/graph", expect.any(Object));
    expect(fetchMock).not.toHaveBeenCalledWith("/api/frontend/modules/event-insight/topics", expect.any(Object));
  });

  it("shows event graph loading state", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise(() => undefined));

    renderWithQueryClient(<EventGraphWorkspace />);

    expect(screen.getByText("正在加载关系网络...")).toBeInTheDocument();
  });

  it("uses draggable graph-library nodes sized by connected edge count and supports edit and delete", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(eventInsightFetch);

    renderWithQueryClient(<EventGraphWorkspace />);

    expect(await screen.findByLabelText("关系网络画布")).toBeInTheDocument();
    expect(await screen.findByTestId("rf-node-event-1")).toHaveAttribute("data-draggable", "true");
    const highDegreeNode = await screen.findByRole("button", { name: "查看节点 存储芯片报价上调" });
    const lowDegreeNode = screen.getByRole("button", { name: "查看节点 数据中心液冷方案渗透率持续上升" });
    expect(Number.parseFloat(highDegreeNode.style.width)).toBeGreaterThan(Number.parseFloat(lowDegreeNode.style.width));

    fireEvent.doubleClick(lowDegreeNode);
    fireEvent.change(screen.getByLabelText("节点标题"), { target: { value: "液冷方案渗透加速" } });
    fireEvent.change(screen.getByLabelText("节点摘要"), { target: { value: "云厂商上修资本开支。" } });
    fireEvent.click(screen.getByRole("button", { name: "保存节点" }));
    expect(screen.getByRole("button", { name: "查看节点 液冷方案渗透加速" })).toBeInTheDocument();

    const editedNode = screen.getByRole("button", { name: "查看节点 液冷方案渗透加速" });
    fireEvent.click(editedNode);
    fireEvent.click(screen.getByRole("button", { name: "删除选中节点" }));
    expect(screen.queryByRole("button", { name: "查看节点 液冷方案渗透加速" })).not.toBeInTheDocument();
  });

  it("creates topics from toolbar buttons and refreshes graph data", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(eventInsightFetch);

    renderWithQueryClient(<TopicTraceWorkspace />);

    expect(await screen.findByText("主题事件")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "新建主题" }));
    fireEvent.change(screen.getByLabelText("主题名称"), { target: { value: "商业航天" } });
    fireEvent.click(screen.getByRole("button", { name: "保存主题" }));
    expect(await screen.findByText("主题已创建：商业航天")).toBeInTheDocument();

    renderWithQueryClient(<EventGraphWorkspace />);

    expect(await screen.findByLabelText("关系网络画布")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "刷新关系网络" }));
    await waitFor(() => expect(fetchMock.mock.calls.filter(([input]) => String(input).includes("/api/frontend/modules/event-insight/graph")).length).toBeGreaterThan(1));
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
      id: "event-3",
      eventId: 3,
      kind: "capacity",
      title: "AI 服务器订单继续上修",
      happenedAt: "2026-05-22T10:30:00+08:00",
      confidence: "中可信 · 73",
      confidenceTone: "amber",
      summary: "AI 服务器供应链景气度延续。",
      left: "74%",
      top: "34%",
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
    {
      id: "relation-2",
      sourceNodeId: "event-1",
      targetNodeId: "event-3",
      type: "follow",
      summary: "涨价信号延伸到服务器订单。",
      left: "31%",
      top: "28%",
      width: "48%",
      rotate: "6deg",
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
    if (url.search.includes("topicId")) throw new Error("Event graph must not depend on topicId");
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
