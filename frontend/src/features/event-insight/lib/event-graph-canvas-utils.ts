import type { GraphEdge, GraphNode, InsightTone } from "../model/event-insight.types";

export const EVENT_GRAPH_CANVAS_WIDTH = 2200;
export const EVENT_GRAPH_CANVAS_HEIGHT = 1200;

const NODE_COLORS: Record<InsightTone, string> = {
  blue: "#2f9bd8",
  green: "#2aa876",
  amber: "#f59e0b",
  rose: "#cf2e54",
  violet: "#8e44ad",
  slate: "#0f5b89",
};

/**
 * 将后端百分比位置转换为画布坐标。
 *
 * @param value 百分比字符串，例如 `58%`。
 * @param size 画布当前维度。
 * @param fallback 解析失败时使用的坐标。
 * @returns 像素坐标。
 */
export function parsePercentPosition(value: string, size: number, fallback: number) {
  const parsed = Number.parseFloat(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.round((parsed / 100) * size);
}

/**
 * 统计每个节点连接的有效关系数量。
 *
 * @param edges 图谱关系边。
 * @returns 节点 ID 到连接数量的映射。
 */
export function buildNodeDegreeMap(edges: GraphEdge[]) {
  const degreeMap = new Map<string, number>();
  for (const edge of edges) {
    if (!edge.sourceNodeId || !edge.targetNodeId) continue;
    degreeMap.set(edge.sourceNodeId, (degreeMap.get(edge.sourceNodeId) ?? 0) + 1);
    degreeMap.set(edge.targetNodeId, (degreeMap.get(edge.targetNodeId) ?? 0) + 1);
  }
  return degreeMap;
}

/**
 * 按连接数量换算节点半径，使节点面积随关系数量递增。
 *
 * @param degree 节点连接的关系数量。
 * @returns 节点圆半径。
 */
export function getNodeRadiusByDegree(degree: number) {
  const baseArea = Math.PI * 11 * 11;
  const extraArea = Math.max(0, degree) * 92;
  return Math.round(Math.sqrt((baseArea + extraArea) / Math.PI));
}

/**
 * 根据可信度色调获得节点颜色。
 *
 * @param tone 后端返回的色调。
 * @returns 节点填充色。
 */
export function getNodeColor(tone: InsightTone) {
  return NODE_COLORS[tone] ?? NODE_COLORS.slate;
}

/**
 * 截断节点和边标签，避免画布标签过长遮挡。
 *
 * @param value 原始文本。
 * @param maxLength 最大字符数。
 * @returns 截断后的展示文本。
 */
export function truncateGraphLabel(value: string, maxLength = 18) {
  if (value.length <= maxLength) return value;
  return `${value.slice(0, maxLength)}...`;
}

/**
 * 计算节点在画布上的初始坐标。
 *
 * @param node 后端图节点。
 * @param index 节点序号，用于缺省坐标回退。
 * @returns 标准化后的画布节点坐标。
 */
export function buildInitialCanvasPosition(node: GraphNode, index: number) {
  const fallbackX = 280 + (index % 6) * 250;
  const fallbackY = 180 + Math.floor(index / 6) * 180;
  return {
    x: parsePercentPosition(node.left, EVENT_GRAPH_CANVAS_WIDTH, fallbackX),
    y: parsePercentPosition(node.top, EVENT_GRAPH_CANVAS_HEIGHT, fallbackY),
  };
}
