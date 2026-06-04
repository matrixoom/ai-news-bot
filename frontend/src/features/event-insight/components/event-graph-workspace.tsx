import { FormEvent, MouseEvent, PointerEvent, useEffect, useMemo, useRef, useState } from "react";
import type { GraphEdge, GraphNode } from "../model/event-insight.types";
import { useEventGraphQuery } from "../hooks/use-event-graph-query";
import {
  EVENT_GRAPH_CANVAS_HEIGHT,
  EVENT_GRAPH_CANVAS_WIDTH,
  buildInitialCanvasPosition,
  buildNodeDegreeMap,
} from "../lib/event-graph-canvas-utils";
import {
  CanvasDeleteButton,
  CanvasToolbar,
  DotGrid,
  EntityLegend,
  GraphEdgePath,
  GraphNodeButton,
  GraphSvgDefs,
  NodeEditDialog,
  type EditingGraphNode,
  type EventGraphCanvasNode,
} from "./event-graph-canvas-parts";

type CanvasNode = EventGraphCanvasNode;

type DragState = {
  nodeId: string;
  offsetX: number;
  offsetY: number;
};

type CanvasMoveEvent = MouseEvent<HTMLElement> | PointerEvent<HTMLElement>;

/**
 * 渲染 MiroFish 风格的关系网络画布。
 *
 * @returns 支持刷新、全屏、节点选择、拖拽、删除和双击编辑的关系网络页面。
 */
export function EventGraphWorkspace() {
  const graphQuery = useEventGraphQuery();
  const graph = graphQuery.data;
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const [nodes, setNodes] = useState<CanvasNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [selectedId, setSelectedId] = useState<string | undefined>();
  const [dragState, setDragState] = useState<DragState | null>(null);
  const [editingNode, setEditingNode] = useState<EditingGraphNode | null>(null);
  const [showEdgeLabels, setShowEdgeLabels] = useState(true);
  const [actionMessage, setActionMessage] = useState("");
  const nodeIds = useMemo(() => new Set(nodes.map((node) => node.id)), [nodes]);
  const visibleEdges = useMemo(
    () => edges.filter((edge) => edge.sourceNodeId && edge.targetNodeId && nodeIds.has(edge.sourceNodeId) && nodeIds.has(edge.targetNodeId)),
    [edges, nodeIds],
  );
  const degreeMap = useMemo(() => buildNodeDegreeMap(visibleEdges), [visibleEdges]);
  const nodeMap = useMemo(() => new Map(nodes.map((node) => [node.id, node])), [nodes]);

  useEffect(() => {
    if (!graph) return;
    setNodes(graph.nodes.map((node, index) => ({ ...node, ...buildInitialCanvasPosition(node, index) })));
    setEdges(graph.edges);
    setSelectedId(graph.selectedNodeId ?? graph.nodes[0]?.id);
  }, [graph, graphQuery.dataUpdatedAt]);

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

  /** 刷新图谱数据并恢复服务端位置。 */
  async function handleRefresh() {
    await graphQuery.refetch();
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
    setEdges((current) => current.filter((edge) => edge.sourceNodeId !== selectedId && edge.targetNodeId !== selectedId));
    setSelectedId(undefined);
    setActionMessage("节点已从当前画布删除。");
  }

  /**
   * 将鼠标指针位置换算为画布坐标。
   *
   * @param event 指针事件。
   * @returns 画布内坐标。
   */
  function getCanvasPoint(event: CanvasMoveEvent) {
    const rect = canvasRef.current?.getBoundingClientRect();
    const width = rect?.width && rect.width > 0 ? rect.width : EVENT_GRAPH_CANVAS_WIDTH;
    const height = rect?.height && rect.height > 0 ? rect.height : EVENT_GRAPH_CANVAS_HEIGHT;
    const left = rect?.left ?? 0;
    const top = rect?.top ?? 0;
    const clientX = Number.isFinite(event.clientX) ? event.clientX : left;
    const clientY = Number.isFinite(event.clientY) ? event.clientY : top;
    return {
      x: ((clientX - left) / width) * EVENT_GRAPH_CANVAS_WIDTH,
      y: ((clientY - top) / height) * EVENT_GRAPH_CANVAS_HEIGHT,
    };
  }

  /**
   * 开始拖动节点。
   *
   * @param event 指针按下事件。
   * @param node 当前节点。
   */
  function handleNodeDragStart(event: MouseEvent<HTMLButtonElement> | PointerEvent<HTMLButtonElement>, node: CanvasNode) {
    event.preventDefault();
    const point = getCanvasPoint(event);
    setSelectedId(node.id);
    setDragState({ nodeId: node.id, offsetX: point.x - node.x, offsetY: point.y - node.y });
  }

  /**
   * 拖动中更新节点坐标。
   *
   * @param event 指针移动事件。
   */
  function handleCanvasDragMove(event: MouseEvent<HTMLDivElement> | PointerEvent<HTMLDivElement>) {
    if (!dragState) return;
    const point = getCanvasPoint(event);
    setNodes((current) =>
      current.map((node) =>
        node.id === dragState.nodeId
          ? {
              ...node,
              x: Math.max(24, Math.min(EVENT_GRAPH_CANVAS_WIDTH - 24, point.x - dragState.offsetX)),
              y: Math.max(24, Math.min(EVENT_GRAPH_CANVAS_HEIGHT - 24, point.y - dragState.offsetY)),
            }
          : node,
      ),
    );
  }

  /** 结束节点拖动。 */
  function handleCanvasDragEnd() {
    setDragState(null);
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
              title: title || node.title,
              summary: summary || node.summary,
            }
          : node,
      ),
    );
    setEditingNode(null);
    setActionMessage("节点信息已更新。");
  }

  return (
    <section className="-m-8 h-[calc(100vh-5rem)] min-h-[720px] overflow-hidden bg-white">
      <h2 className="sr-only">关系网络</h2>
      <div
        aria-label="关系网络画布"
        className="relative h-full w-full cursor-default overflow-hidden bg-white text-slate-700"
        onMouseLeave={handleCanvasDragEnd}
        onMouseMove={handleCanvasDragMove}
        onMouseUp={handleCanvasDragEnd}
        onPointerLeave={handleCanvasDragEnd}
        onPointerMove={handleCanvasDragMove}
        onPointerUp={handleCanvasDragEnd}
        ref={canvasRef}
      >
        <DotGrid />
        <div className="absolute left-4 top-5 z-20 text-sm font-semibold text-slate-700">Graph Relationship Visualization</div>
        <CanvasToolbar
          onFullscreen={handleFullscreen}
          onRefresh={handleRefresh}
          onShowEdgeLabelsChange={setShowEdgeLabels}
          showEdgeLabels={showEdgeLabels}
        />
        <EntityLegend />
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
        <svg
          aria-hidden="true"
          className="absolute inset-0 h-full w-full"
          preserveAspectRatio="xMidYMid meet"
          viewBox={`0 0 ${EVENT_GRAPH_CANVAS_WIDTH} ${EVENT_GRAPH_CANVAS_HEIGHT}`}
        >
          <GraphSvgDefs />
          {visibleEdges.map((edge) => (
            <GraphEdgePath edge={edge} key={edge.id} nodeMap={nodeMap} showLabel={showEdgeLabels} />
          ))}
        </svg>
        <div
          className="absolute inset-0"
          style={{
            height: EVENT_GRAPH_CANVAS_HEIGHT,
            transformOrigin: "top left",
            width: EVENT_GRAPH_CANVAS_WIDTH,
          }}
        >
          {nodes.map((node) => {
            return (
              <GraphNodeButton
                degree={degreeMap.get(node.id) ?? 0}
                key={node.id}
                node={node}
                onDoubleClick={() => setEditingNode(node)}
                onMouseDown={(event) => handleNodeDragStart(event, node)}
                onPointerDown={(event) => handleNodeDragStart(event, node)}
                selected={selectedId === node.id}
              />
            );
          })}
        </div>
      </div>
      {editingNode ? (
        <NodeEditDialog node={editingNode} onCancel={() => setEditingNode(null)} onSubmit={handleEditSubmit} />
      ) : null}
    </section>
  );
}
