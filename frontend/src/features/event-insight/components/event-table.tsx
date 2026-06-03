import { formatLocalDateTime } from "../../../shared/utils/format-local-date-time";
import type { EventInsightApiEvent, InsightTone } from "../model/event-insight.types";
import { InsightBadge } from "./event-insight-shell";

type EventTableProps = {
  events: EventInsightApiEvent[];
  selectedId: number | null;
  onSelect: (eventId: number) => void;
};

const eventTypeLabels: Record<string, string> = {
  policy: "政策",
  price_change: "价格变化",
  supply_demand: "供需变化",
  order_contract: "订单合同",
  capacity: "产能",
  earnings: "业绩",
  technology: "技术",
  capital_market: "资本市场",
  institution_view: "机构观点",
  macro: "宏观",
  risk: "风险",
  other: "其他",
};

const statusLabels: Record<string, string> = {
  active: "活跃",
  ignored: "已忽略",
  archived: "已归档",
};

/** 渲染结构化事件表格。 */
export function EventTable({ events, selectedId, onSelect }: EventTableProps) {
  if (events.length === 0) {
    return <div className="p-8 text-center text-sm text-slate-500">暂无事件，先导入材料或调整筛选条件。</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-[880px] table-fixed text-left text-xs">
        <thead className="border-b border-slate-200 bg-slate-50 text-slate-500">
          <tr>
            <th className="w-[36%] px-3 py-3">事件</th>
            <th className="px-3 py-3">类型</th>
            <th className="px-3 py-3">可信度</th>
            <th className="px-3 py-3">主题</th>
            <th className="px-3 py-3">发生时间</th>
            <th className="px-3 py-3">状态</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => (
            <tr className={`border-b border-slate-100 ${selectedId === event.id ? "bg-blue-50" : "hover:bg-slate-50"}`} key={event.id}>
              <td className="px-3 py-3">
                <button aria-label={`查看 ${event.title}`} className="block text-left" onClick={() => onSelect(event.id)} type="button">
                  <strong className="block text-xs text-slate-950">{event.title}</strong>
                  <span className="mt-1 line-clamp-2 block text-[11px] text-slate-500">{event.summary}</span>
                </button>
              </td>
              <td className="px-3 py-3">
                <InsightBadge tone="blue">{eventTypeLabels[event.eventType] ?? event.eventType}</InsightBadge>
              </td>
              <td className="px-3 py-3">
                <InsightBadge tone={confidenceTone(event.confidenceScore)}>{Math.round(event.confidenceScore * 100)}%</InsightBadge>
              </td>
              <td className="px-3 py-3 text-slate-700">{event.topics?.[0]?.name ?? "未归属"}</td>
              <td className="px-3 py-3 text-slate-600">{formatLocalDateTime(event.eventTime)}</td>
              <td className="px-3 py-3">
                <InsightBadge tone={statusTone(event.manualStatus)}>{statusLabels[event.manualStatus] ?? event.manualStatus}</InsightBadge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** 按置信度返回徽标颜色。 */
function confidenceTone(score: number): InsightTone {
  if (score >= 0.8) return "green";
  if (score >= 0.6) return "amber";
  return "rose";
}

/** 按人工状态返回徽标颜色。 */
function statusTone(status: string): InsightTone {
  if (status === "active") return "green";
  if (status === "ignored") return "amber";
  return "slate";
}
