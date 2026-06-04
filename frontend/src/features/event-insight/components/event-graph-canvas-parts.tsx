import {
  ArrowPathIcon,
  ArrowsPointingOutIcon,
  PencilSquareIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import { FormEvent, type MouseEventHandler, type PointerEventHandler } from "react";
import type { GraphEdge, GraphNode } from "../model/event-insight.types";
import {
  EVENT_GRAPH_CANVAS_HEIGHT,
  EVENT_GRAPH_CANVAS_WIDTH,
  getNodeColor,
  getNodeRadiusByDegree,
  truncateGraphLabel,
} from "../lib/event-graph-canvas-utils";

export type EventGraphCanvasNode = GraphNode & {
  x: number;
  y: number;
};

export type EditingGraphNode = Pick<EventGraphCanvasNode, "id" | "kind" | "summary" | "title">;

/**
 * 渲染画布顶部刷新、全屏和边标签开关。
 *
 * @param props 控制状态与操作回调。
 * @returns 画布悬浮工具条。
 */
export function CanvasToolbar({
  showEdgeLabels,
  onFullscreen,
  onRefresh,
  onShowEdgeLabelsChange,
}: {
  showEdgeLabels: boolean;
  onFullscreen: () => void;
  onRefresh: () => void;
  onShowEdgeLabelsChange: (value: boolean) => void;
}) {
  return (
    <>
      <div className="absolute right-5 top-5 z-30 flex items-center gap-2">
        <button
          aria-label="刷新关系网络"
          className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-200 bg-white/95 px-4 text-sm font-medium text-slate-600 shadow-sm transition hover:border-slate-300 hover:text-slate-900"
          onClick={onRefresh}
          type="button"
        >
          <ArrowPathIcon aria-hidden="true" className="h-4 w-4" />
          Refresh
        </button>
        <button
          aria-label="全屏画布"
          className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-slate-200 bg-white/95 text-slate-500 shadow-sm transition hover:border-slate-300 hover:text-slate-900"
          onClick={onFullscreen}
          type="button"
        >
          <ArrowsPointingOutIcon aria-hidden="true" className="h-4 w-4" />
        </button>
      </div>
      <div className="absolute right-5 top-[4.75rem] z-30 flex items-center gap-2 rounded-full border border-slate-100 bg-white/95 px-4 py-3 text-sm text-slate-500 shadow-lg">
        <label className="flex cursor-pointer items-center gap-3">
          <input
            aria-label="显示关系标签"
            checked={showEdgeLabels}
            className="sr-only"
            onChange={(event) => onShowEdgeLabelsChange(event.target.checked)}
            type="checkbox"
          />
          <span className={`flex h-6 w-12 items-center rounded-full p-0.5 transition ${showEdgeLabels ? "bg-purple-600" : "bg-slate-300"}`}>
            <span className={`h-5 w-5 rounded-full bg-white shadow-sm transition ${showEdgeLabels ? "translate-x-6" : ""}`} />
          </span>
          Show Edge Labels
        </label>
      </div>
    </>
  );
}

/**
 * 渲染删除选中节点按钮。
 *
 * @param props 选中状态与删除回调。
 * @returns 画布右下角删除按钮。
 */
export function CanvasDeleteButton({ disabled, onDelete }: { disabled: boolean; onDelete: () => void }) {
  return (
    <div className="absolute bottom-5 right-5 z-30 flex items-center gap-2">
      <button
        aria-label="删除选中节点"
        className="inline-flex h-10 items-center gap-2 rounded-md border border-rose-200 bg-white/95 px-3 text-sm font-medium text-rose-600 shadow-sm transition hover:border-rose-300 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-300"
        disabled={disabled}
        onClick={onDelete}
        type="button"
      >
        <TrashIcon aria-hidden="true" className="h-4 w-4" />
        删除
      </button>
    </div>
  );
}

/**
 * 渲染点阵背景。
 *
 * @returns 画布底层点阵。
 */
export function DotGrid() {
  return (
    <div
      aria-hidden="true"
      className="absolute inset-0"
      style={{
        backgroundImage: "radial-gradient(circle, rgba(148, 163, 184, 0.38) 1.35px, transparent 1.35px)",
        backgroundPosition: "0 0",
        backgroundSize: "34px 34px",
      }}
    />
  );
}

/**
 * 渲染 MiroFish 风格实体类型图例。
 *
 * @returns 左下角图例。
 */
export function EntityLegend() {
  return (
    <div className="absolute bottom-5 left-5 z-30 rounded-lg border border-slate-200 bg-white/95 p-4 text-sm shadow-lg">
      <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-pink-500">Entity Types</h3>
      <div className="grid grid-cols-2 gap-x-5 gap-y-2">
        {ENTITY_LEGEND_ITEMS.map((item) => (
          <span className="flex items-center gap-2 text-slate-500" key={item.label}>
            <i className="h-3 w-3 rounded-full" style={{ backgroundColor: item.color }} />
            {item.label}
          </span>
        ))}
      </div>
    </div>
  );
}

/**
 * 渲染图谱节点。
 *
 * @param props 节点、度数、选择状态和交互回调。
 * @returns 画布上的圆形节点按钮。
 */
export function GraphNodeButton({
  degree,
  node,
  selected,
  onDoubleClick,
  onMouseDown,
  onPointerDown,
}: {
  degree: number;
  node: EventGraphCanvasNode;
  selected: boolean;
  onDoubleClick: () => void;
  onMouseDown: MouseEventHandler<HTMLButtonElement>;
  onPointerDown: PointerEventHandler<HTMLButtonElement>;
}) {
  const radius = getNodeRadiusByDegree(degree);

  return (
    <button
      aria-label={`查看节点 ${node.title}`}
      aria-pressed={selected}
      className="group absolute rounded-full outline-none transition-[box-shadow,filter] hover:brightness-105 focus-visible:ring-4 focus-visible:ring-purple-200"
      onDoubleClick={onDoubleClick}
      onMouseDown={onMouseDown}
      onPointerDown={onPointerDown}
      style={{
        backgroundColor: getNodeColor(node.confidenceTone),
        boxShadow: selected ? "0 0 0 5px rgba(126, 34, 206, 0.2), 0 8px 20px rgba(15, 23, 42, 0.16)" : "0 4px 12px rgba(15, 23, 42, 0.12)",
        height: `${radius * 2}px`,
        left: `${node.x - radius}px`,
        top: `${node.y - radius}px`,
        width: `${radius * 2}px`,
      }}
      type="button"
    >
      <span className="sr-only">{node.summary}</span>
      <span className="pointer-events-none absolute left-[calc(100%+8px)] top-1/2 max-w-[128px] -translate-y-1/2 truncate whitespace-nowrap text-left text-[11px] font-medium text-slate-600">
        {truncateGraphLabel(node.title)}
      </span>
    </button>
  );
}

/**
 * 渲染一条图谱关系边。
 *
 * @param props 关系边、节点索引和标签显示状态。
 * @returns SVG 边路径。
 */
export function GraphEdgePath({ edge, nodeMap, showLabel }: { edge: GraphEdge; nodeMap: Map<string, EventGraphCanvasNode>; showLabel: boolean }) {
  if (!edge.sourceNodeId || !edge.targetNodeId) return null;
  const source = nodeMap.get(edge.sourceNodeId);
  const target = nodeMap.get(edge.targetNodeId);
  if (!source || !target) return null;
  const midX = (source.x + target.x) / 2;
  const midY = (source.y + target.y) / 2;
  const curveOffset = Math.min(56, Math.max(-56, (target.x - source.x) / 12));
  const path = `M ${source.x} ${source.y} Q ${midX} ${midY - curveOffset} ${target.x} ${target.y}`;

  return (
    <g>
      <path d={path} fill="none" markerEnd="url(#edge-arrow)" stroke="rgba(100, 116, 139, 0.34)" strokeLinecap="round" strokeWidth="2" />
      {showLabel && edge.summary ? (
        <text fill="#6b7280" fontSize="11" fontWeight="600" textAnchor="middle" x={midX} y={midY - curveOffset / 2 - 5}>
          {truncateGraphLabel(edge.summary, 22)}
        </text>
      ) : null}
    </g>
  );
}

/**
 * 渲染 SVG 箭头定义。
 *
 * @returns SVG defs。
 */
export function GraphSvgDefs() {
  return (
    <defs>
      <marker id="edge-arrow" markerHeight="7" markerWidth="7" orient="auto" refX="6" refY="3.5">
        <path d="M0,0 L7,3.5 L0,7 Z" fill="rgba(100, 116, 139, 0.32)" />
      </marker>
    </defs>
  );
}

/**
 * 渲染节点编辑弹窗。
 *
 * @param props 当前节点、取消回调和提交回调。
 * @returns 节点编辑表单。
 */
export function NodeEditDialog({
  node,
  onCancel,
  onSubmit,
}: {
  node: EditingGraphNode;
  onCancel: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/35 px-4">
      <form aria-label="编辑节点" className="w-full max-w-md rounded-xl bg-white p-5 shadow-2xl" onSubmit={onSubmit}>
        <div className="mb-4 flex items-center gap-2">
          <PencilSquareIcon aria-hidden="true" className="h-5 w-5 text-purple-600" />
          <h3 className="text-base font-semibold text-slate-950">编辑节点</h3>
        </div>
        <label className="grid gap-2 text-sm font-semibold text-slate-700">
          节点标题
          <input className="rounded-md border border-slate-300 px-3 py-2 font-normal" defaultValue={node.title} name="title" />
        </label>
        <label className="mt-4 grid gap-2 text-sm font-semibold text-slate-700">
          节点摘要
          <textarea className="min-h-24 rounded-md border border-slate-300 px-3 py-2 font-normal" defaultValue={node.summary} name="summary" />
        </label>
        <p className="mt-3 text-xs text-slate-500">类型：{node.kind}</p>
        <div className="mt-5 flex justify-end gap-2">
          <button className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700" onClick={onCancel} type="button">
            取消
          </button>
          <button className="rounded-md bg-purple-600 px-4 py-2 text-sm font-semibold text-white" type="submit">
            保存节点
          </button>
        </div>
      </form>
    </div>
  );
}

const ENTITY_LEGEND_ITEMS = [
  { label: "University", color: "#ff6b35" },
  { label: "Entity", color: "#0f5b89" },
  { label: "Alumni", color: "#8e44ad" },
  { label: "Organization", color: "#2aa876" },
  { label: "Student", color: "#cf2e54" },
  { label: "Person", color: "#2f9bd8" },
  { label: "Media Outlet", color: "#9b59b6" },
  { label: "Legal Authority", color: "#27ae60" },
  { label: "Opinion Leader", color: "#f59e0b" },
  { label: "Government Agency", color: "#f97316" },
] as const;
