import {
  ArrowPathIcon,
  ArrowsPointingOutIcon,
  PencilSquareIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import {
  BaseEdge,
  EdgeLabelRenderer,
  Handle,
  Position,
  getBezierPath,
  type EdgeProps,
  type NodeProps,
} from "@xyflow/react";
import { FormEvent } from "react";
import type { Edge, Node } from "@xyflow/react";
import type { GraphNode, InsightTone } from "../model/event-insight.types";
import { getNodeColor, getNodeRadiusByDegree, truncateGraphLabel } from "../lib/event-graph-canvas-utils";

export type EditingGraphNode = Pick<GraphNode, "id" | "kind" | "summary" | "title">;

export type EventFlowNodeData = Record<string, unknown> & {
  confidenceTone: InsightTone;
  degree: number;
  kind: string;
  onEdit: (node: EditingGraphNode) => void;
  onSelect: (nodeId: string) => void;
  summary: string;
  title: string;
};

export type EventFlowEdgeData = Record<string, unknown> & {
  label: string;
  showLabel: boolean;
};

export type EventFlowNode = Node<EventFlowNodeData, "eventNode">;
export type EventFlowEdge = Edge<EventFlowEdgeData, "eventEdge">;

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
 * 渲染 React Flow 自定义圆形事件节点。
 *
 * @param props React Flow 注入的节点数据与选择状态。
 * @returns 可选择、可双击编辑的关系网络节点。
 */
export function EventFlowNodeView({ data, id, selected }: NodeProps<EventFlowNode>) {
  const radius = getNodeRadiusByDegree(data.degree);
  const size = radius * 2;
  const nodeForEdit: EditingGraphNode = {
    id,
    kind: data.kind,
    summary: data.summary,
    title: data.title,
  };

  return (
    <div className="relative flex items-center">
      <Handle className="opacity-0" position={Position.Left} type="target" />
      <button
        aria-label={`查看节点 ${data.title}`}
        aria-pressed={selected}
        className="group relative rounded-full outline-none transition-[box-shadow,filter] hover:brightness-105 focus-visible:ring-4 focus-visible:ring-purple-200"
        onClick={() => data.onSelect(id)}
        onDoubleClick={() => data.onEdit(nodeForEdit)}
        style={{
          backgroundColor: getNodeColor(data.confidenceTone),
          boxShadow: selected ? "0 0 0 5px rgba(126, 34, 206, 0.2), 0 8px 20px rgba(15, 23, 42, 0.16)" : "0 4px 12px rgba(15, 23, 42, 0.12)",
          height: `${size}px`,
          width: `${size}px`,
        }}
        type="button"
      >
        <span className="sr-only">{data.summary}</span>
      </button>
      <span className="pointer-events-none ml-2 max-w-[148px] truncate whitespace-nowrap text-left text-[11px] font-semibold text-slate-600">
        {truncateGraphLabel(data.title)}
      </span>
      <Handle className="opacity-0" position={Position.Right} type="source" />
    </div>
  );
}

/**
 * 渲染 React Flow 自定义贝塞尔关系边。
 *
 * @param props React Flow 注入的边位置与数据。
 * @returns 带可选标签的 MiroFish 风格关系线。
 */
export function EventFlowEdgeView({
  data,
  markerEnd,
  sourcePosition,
  sourceX,
  sourceY,
  targetPosition,
  targetX,
  targetY,
}: EdgeProps<EventFlowEdge>) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourcePosition,
    sourceX,
    sourceY,
    targetPosition,
    targetX,
    targetY,
  });

  return (
    <>
      <BaseEdge markerEnd={markerEnd} path={edgePath} style={{ stroke: "rgba(100, 116, 139, 0.34)", strokeWidth: 2 }} />
      {data?.showLabel && data.label ? (
        <EdgeLabelRenderer>
          <div
            className="pointer-events-none absolute max-w-[180px] -translate-x-1/2 -translate-y-1/2 truncate bg-white/65 px-1 text-[10px] font-semibold text-slate-500"
            style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
          >
            {truncateGraphLabel(data.label, 28)}
          </div>
        </EdgeLabelRenderer>
      ) : null}
    </>
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
