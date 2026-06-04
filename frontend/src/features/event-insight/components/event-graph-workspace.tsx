import "@xyflow/react/dist/style.css";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  MarkerType,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type EdgeTypes,
  type NodeTypes,
  type OnSelectionChangeFunc,
} from "@xyflow/react";
import type { GraphEdge, GraphNode } from "../model/event-insight.types";
import { useEventGraphQuery } from "../hooks/use-event-graph-query";
import { buildInitialCanvasPosition, buildNodeDegreeMap } from "../lib/event-graph-canvas-utils";
import {
  CanvasDeleteButton,
  CanvasToolbar,
  EventFlowEdgeView,
  EventFlowNodeView,
  NodeEditDialog,
  type EditingGraphNode,
  type EventFlowEdge,
  type EventFlowNode,
} from "./event-graph-canvas-parts";

const NODE_TYPES: NodeTypes = { eventNode: EventFlowNodeView };
const EDGE_TYPES: EdgeTypes = { eventEdge: EventFlowEdgeView };

/**
 * 渲染 MiroFish 风格的关系网络画布。
 *
 * @returns 支持刷新、全屏、节点选择、拖拽、删除和双击编辑的关系网络页面。
 */
export function EventGraphWorkspace() {
  return (
    <ReactFlowProvider>
      <EventGraphWorkspaceCanvas />
    </ReactFlowProvider>
  );
}

/**
 * 渲染 React Flow 关系网络主体。
 *
 * @returns React Flow 驱动的全屏关系网络。
 */
function EventGraphWorkspaceCanvas() {
  const graphQuery = useEventGraphQuery();
  const graph = graphQuery.data;
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const reactFlow = useReactFlow<EventFlowNode, EventFlowEdge>();
  const fitViewRef = useRef(reactFlow.fitView);
  const [nodes, setNodes, onNodesChange] = useNodesState<EventFlowNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<EventFlowEdge>([]);
  const [selectedId, setSelectedId] = useState<string | undefined>();
  const [editingNode, setEditingNode] = useState<EditingGraphNode | null>(null);
  const [showEdgeLabels, setShowEdgeLabels] = useState(true);
  const [actionMessage, setActionMessage] = useState("");

  useEffect(() => {
    fitViewRef.current = reactFlow.fitView;
  }, [reactFlow.fitView]);

  const openNodeEditor = useCallback((node: EditingGraphNode) => {
    setEditingNode(node);
  }, []);

  const selectNode = useCallback((nodeId: string) => {
    setSelectedId(nodeId);
    setNodes((current) => current.map((node) => ({ ...node, selected: node.id === nodeId })));
  }, [setNodes]);

  useEffect(() => {
    if (!graph) return;
    const validEdges = buildVisibleGraphEdges(graph.edges, graph.nodes);
    const degreeMap = buildNodeDegreeMap(validEdges);
    const selectedNodeId = graph.selectedNodeId ?? graph.nodes[0]?.id;

    setNodes(graph.nodes.map((node, index) => buildFlowNode(node, index, degreeMap, selectedNodeId, selectNode, openNodeEditor)));
    setEdges(validEdges.map((edge) => buildFlowEdge(edge, showEdgeLabels)));
    setSelectedId(selectedNodeId);
    window.setTimeout(() => fitViewRef.current({ duration: 260, padding: 0.28 }), 0);
  }, [graph, graphQuery.dataUpdatedAt, openNodeEditor, selectNode, setEdges, setNodes, showEdgeLabels]);

  useEffect(() => {
    setEdges((current) => current.map((edge) => ({ ...edge, data: { label: edge.data?.label ?? "", showLabel: showEdgeLabels } })));
  }, [setEdges, showEdgeLabels]);

  useEffect(() => {
    /** 处理键盘删除选中节点。 */
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== "Delete" && event.key !== "Backspace") return;
      if (!selectedId || editingNode) return;
      event.preventDefault();
      deleteSelectedNode();
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [editingNode, selectedId]);

  /** 刷新图谱数据并重新适配画布视口。 */
  async function handleRefresh() {
    await graphQuery.refetch();
    fitViewRef.current({ duration: 260, padding: 0.28 });
    setActionMessage("关系网络已刷新。");
  }

  /** 请求浏览器进入全屏画布模式。 */
  function handleFullscreen() {
    void canvasRef.current?.requestFullscreen?.();
  }

  /** 删除当前选中节点及其关联边。 */
  function deleteSelectedNode() {
    if (!selectedId) return;
    setNodes((current) => current.filter((node) => node.id !== selectedId));
    setEdges((current) => current.filter((edge) => edge.source !== selectedId && edge.target !== selectedId));
    setSelectedId(undefined);
    setActionMessage("节点已从当前画布删除。");
  }

  /** 保存双击编辑后的节点信息。 */
  function handleEditSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingNode) return;
    const formData = new FormData(event.currentTarget);
    const title = String(formData.get("title") ?? "").trim();
    const summary = String(formData.get("summary") ?? "").trim();
    setNodes((current) =>
      current.map((node) =>
        node.id === editingNode.id
          ? {
              ...node,
              data: {
                ...node.data,
                summary: summary || node.data.summary,
                title: title || node.data.title,
              },
            }
          : node,
      ),
    );
    setEditingNode(null);
    setActionMessage("节点信息已更新。");
  }

  const handleSelectionChange: OnSelectionChangeFunc<EventFlowNode, EventFlowEdge> = useCallback(({ nodes: selectedNodes }) => {
    setSelectedId(selectedNodes[0]?.id);
  }, []);

  const defaultEdgeOptions = useMemo(
    () => ({
      markerEnd: { color: "rgba(100, 116, 139, 0.4)", type: MarkerType.ArrowClosed },
    }),
    [],
  );

  return (
    <section className="-m-8 h-[calc(100vh-5rem)] min-h-[720px] overflow-hidden bg-white">
      <h2 className="sr-only">关系网络</h2>
      <div className="relative h-full w-full overflow-hidden bg-white text-slate-700" ref={canvasRef}>
        <div className="absolute left-4 top-5 z-20 text-sm font-semibold text-slate-700">Graph Relationship Visualization</div>
        <ReactFlow
          aria-label="关系网络画布"
          className="event-graph-flow"
          defaultEdgeOptions={defaultEdgeOptions}
          deleteKeyCode={["Backspace", "Delete"]}
          edgeTypes={EDGE_TYPES}
          edges={edges}
          fitView
          maxZoom={2.2}
          minZoom={0.18}
          nodeTypes={NODE_TYPES}
          nodes={nodes}
          nodesConnectable={false}
          onEdgesChange={onEdgesChange}
          onNodesChange={onNodesChange}
          onPaneClick={() => setSelectedId(undefined)}
          onSelectionChange={handleSelectionChange}
          panOnScroll
          selectionOnDrag
        >
          <Background color="#cbd5e1" gap={34} size={1.35} variant={BackgroundVariant.Dots} />
          <Controls showInteractive={false} />
        </ReactFlow>
        <CanvasToolbar
          onFullscreen={handleFullscreen}
          onRefresh={handleRefresh}
          onShowEdgeLabelsChange={setShowEdgeLabels}
          showEdgeLabels={showEdgeLabels}
        />
        <CanvasDeleteButton disabled={!selectedId} onDelete={deleteSelectedNode} />
        {actionMessage ? (
          <div className="absolute left-1/2 top-5 z-30 -translate-x-1/2 rounded-full border border-emerald-100 bg-white/95 px-4 py-2 text-sm text-emerald-700 shadow">
            {actionMessage}
          </div>
        ) : null}
        {graphQuery.isLoading ? (
          <div className="absolute inset-0 z-40 grid place-items-center bg-white/60 text-sm text-slate-500">正在加载关系网络...</div>
        ) : null}
        {graphQuery.isError ? (
          <div className="absolute inset-0 z-40 grid place-items-center bg-white/80 text-sm text-rose-700">关系网络加载失败，请检查事件网络数据。</div>
        ) : null}
        {nodes.length === 0 && !graphQuery.isLoading ? (
          <div className="absolute left-5 top-16 rounded-md border border-dashed border-slate-300 bg-white/95 p-4 text-sm text-slate-500">暂无可展示节点。</div>
        ) : null}
      </div>
      {editingNode ? <NodeEditDialog node={editingNode} onCancel={() => setEditingNode(null)} onSubmit={handleEditSubmit} /> : null}
    </section>
  );
}

/**
 * 过滤掉端点缺失的关系边。
 *
 * @param edges 后端关系边。
 * @param nodes 后端节点列表。
 * @returns 两端节点都存在的关系边。
 */
function buildVisibleGraphEdges(edges: GraphEdge[], nodes: GraphNode[]) {
  const nodeIds = new Set(nodes.map((node) => node.id));
  return edges.filter((edge) => edge.sourceNodeId && edge.targetNodeId && nodeIds.has(edge.sourceNodeId) && nodeIds.has(edge.targetNodeId));
}

/**
 * 将后端节点映射为 React Flow 节点。
 *
 * @param node 后端图节点。
 * @param index 节点序号，用作缺省布局回退。
 * @param degreeMap 节点连接数映射。
 * @param selectedId 当前选中节点 ID。
 * @param onSelect 节点选择回调。
 * @param onEdit 节点编辑回调。
 * @returns React Flow 节点。
 */
function buildFlowNode(
  node: GraphNode,
  index: number,
  degreeMap: Map<string, number>,
  selectedId: string | undefined,
  onSelect: (nodeId: string) => void,
  onEdit: (node: EditingGraphNode) => void,
): EventFlowNode {
  return {
    data: {
      confidenceTone: node.confidenceTone,
      degree: degreeMap.get(node.id) ?? 0,
      kind: node.kind,
      onEdit,
      onSelect,
      summary: node.summary,
      title: node.title,
    },
    draggable: true,
    id: node.id,
    position: buildInitialCanvasPosition(node, index),
    selected: selectedId === node.id,
    type: "eventNode",
  };
}

/**
 * 将后端关系边映射为 React Flow 边。
 *
 * @param edge 后端关系边。
 * @param showLabel 是否显示关系标签。
 * @returns React Flow 边。
 */
function buildFlowEdge(edge: GraphEdge, showLabel: boolean): EventFlowEdge {
  return {
    data: {
      label: edge.summary ?? "",
      showLabel,
    },
    id: edge.id,
    source: edge.sourceNodeId ?? "",
    target: edge.targetNodeId ?? "",
    type: "eventEdge",
  };
}
