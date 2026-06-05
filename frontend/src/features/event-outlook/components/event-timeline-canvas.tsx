import { useState, type CSSProperties, type MouseEvent as ReactMouseEvent, type ReactNode, type WheelEvent as ReactWheelEvent } from "react";
import type { EventOutlookEvent } from "../model/event-outlook.types";

type EventTimelineCanvasProps = {
  events: EventOutlookEvent[];
  startDate: string;
  endDate: string;
  toolbar: ReactNode;
  onSelectEvent: (event: EventOutlookEvent) => void;
  onRangeChange: (startDate: string, endDate: string) => void;
};

type TimelineTick = {
  id: string;
  label: string;
  leftPct: number;
};

type PositionedEvent = {
  event: EventOutlookEvent;
  leftPct: number;
  side: "above" | "below";
  topPx: number;
  connectorPx: number;
};

type EventNodeStyle = CSSProperties & {
  "--connector-height": string;
};

type DragSelection = {
  startX: number;
  currentX: number;
};

const TRACK_HEIGHT_PX = 580;
const AXIS_Y_PX = 292;
const EVENT_CARD_HEIGHT_PX = 66;
const EVENT_CONNECTOR_GAP_PX = 38;
const EVENT_STACK_GAP_PX = 76;
const MIN_ZOOM_DAYS = 7;
const MAX_ZOOM_DAYS = 730;

/**
 * 将 ISO 日期按浏览器本地时区解析为日期对象。
 * @param value ISO 日期字符串，格式为 YYYY-MM-DD。
 * @returns 解析成功时返回 Date，否则返回 null。
 */
function parseIsoDate(value: string): Date | null {
  const parsed = new Date(`${value}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

/**
 * 将日期对象转换为浏览器本地时区下的 ISO 日期。
 * @param value 日期对象。
 * @returns YYYY-MM-DD 格式的本地日期。
 */
function toLocalIsoDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/**
 * 按指定天数偏移日期。
 * @param value 原始日期。
 * @param days 偏移天数，可为小数。
 * @returns 偏移后的日期。
 */
function addDays(value: Date, days: number): Date {
  return new Date(value.getTime() + days * 24 * 60 * 60 * 1000);
}

/**
 * 生成兜底结束日期，避免非法日期导致时间轴跨度为 0。
 * @param startDate 起始日期。
 * @returns 起始日期之后一年的日期对象。
 */
function addFallbackYear(startDate: Date): Date {
  const endDate = new Date(startDate);
  endDate.setFullYear(endDate.getFullYear() + 1);
  return endDate;
}

/**
 * 限制百分比位置，避免边缘事件被画布裁切。
 * @param value 原始百分比。
 * @returns 限制在可读范围内的百分比。
 */
function clampTimelinePercent(value: number): number {
  return Math.min(96, Math.max(4, value));
}

/**
 * 限制交互百分比，保证框选范围不会跑出画布。
 * @param value 原始百分比。
 * @returns 0 到 1 之间的比例。
 */
function clampInteractionRatio(value: number): number {
  return Math.min(1, Math.max(0, value));
}

/**
 * 计算事件日期在当前时间范围中的横向位置。
 * @param eventDate 事件日期。
 * @param startDate 时间轴起始日期。
 * @param endDate 时间轴结束日期。
 * @returns 事件在画布中的百分比位置。
 */
function getDatePercent(eventDate: Date, startDate: Date, endDate: Date): number {
  const span = Math.max(1, endDate.getTime() - startDate.getTime());
  return clampTimelinePercent(((eventDate.getTime() - startDate.getTime()) / span) * 100);
}

/**
 * 将画布中的横向坐标转换为时间范围内的日期。
 * @param clientX 鼠标横向坐标。
 * @param track 画布 DOM 元素。
 * @param startDate 当前起始日期。
 * @param endDate 当前结束日期。
 * @returns 鼠标所在位置对应的日期。
 */
function getDateFromClientX(clientX: number, track: HTMLDivElement, startDate: Date, endDate: Date): Date {
  const rect = track.getBoundingClientRect();
  const ratio = clampInteractionRatio((clientX - rect.left) / Math.max(1, rect.width));
  const spanMs = endDate.getTime() - startDate.getTime();
  return new Date(startDate.getTime() + spanMs * ratio);
}

/**
 * 读取鼠标在画布内的横向坐标。
 * @param clientX 鼠标横向坐标。
 * @param track 画布 DOM 元素。
 * @returns 限制在画布宽度内的像素位置。
 */
function getTrackX(clientX: number, track: HTMLDivElement): number {
  const rect = track.getBoundingClientRect();
  return Math.min(rect.width, Math.max(0, clientX - rect.left));
}

/**
 * 判断两个日期是否构成可用的缩放窗口。
 * @param startDate 起始日期。
 * @param endDate 结束日期。
 * @returns 日期跨度足够时返回 true。
 */
function isUsableRange(startDate: Date, endDate: Date): boolean {
  return endDate.getTime() - startDate.getTime() >= MIN_ZOOM_DAYS * 24 * 60 * 60 * 1000;
}

/**
 * 格式化月度刻度文案。
 * @param value 需要展示的日期。
 * @returns YYYY-MM 格式的刻度文案。
 */
function formatMonthLabel(value: Date): string {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}`;
}

/**
 * 生成当前时间范围内的月度刻度。
 * @param startDate 时间轴起始日期。
 * @param endDate 时间轴结束日期。
 * @returns 可渲染的刻度列表。
 */
function buildTimelineTicks(startDate: Date, endDate: Date): TimelineTick[] {
  const ticks: TimelineTick[] = [];
  const cursor = new Date(startDate.getFullYear(), startDate.getMonth(), 1);
  cursor.setMonth(cursor.getMonth() + 1);

  while (cursor <= endDate && ticks.length < 18) {
    ticks.push({
      id: cursor.toISOString(),
      label: formatMonthLabel(cursor),
      leftPct: getDatePercent(cursor, startDate, endDate),
    });
    cursor.setMonth(cursor.getMonth() + 1);
  }

  return ticks;
}

/**
 * 按日期分组并排序事件，保证同一刻度的堆叠顺序稳定。
 * @param events 原始事件列表。
 * @returns 按事件日期分组后的列表。
 */
function groupEventsByDate(events: EventOutlookEvent[]): EventOutlookEvent[][] {
  const groups = new Map<string, EventOutlookEvent[]>();

  for (const event of events) {
    const currentGroup = groups.get(event.event_date) ?? [];
    currentGroup.push(event);
    groups.set(event.event_date, currentGroup);
  }

  return Array.from(groups.entries())
    .sort(([leftDate], [rightDate]) => leftDate.localeCompare(rightDate))
    .map(([, group]) => [...group].sort((left, right) => left.id - right.id));
}

/**
 * 计算每条事件在画布中的坐标、上下方向和连接线长度。
 * @param events 事件列表。
 * @param startDate 时间轴起始日期。
 * @param endDate 时间轴结束日期。
 * @returns 带定位信息的事件列表。
 */
function positionTimelineEvents(events: EventOutlookEvent[], startDate: Date, endDate: Date): PositionedEvent[] {
  return groupEventsByDate(events).flatMap((group, groupIndex) =>
    group.map((event, eventIndex) => {
      const eventDate = parseIsoDate(event.event_date) ?? startDate;
      const side = (groupIndex + eventIndex) % 2 === 0 ? "above" : "below";
      const stackIndex = Math.floor(eventIndex / 2);
      const topPx =
        side === "above"
          ? AXIS_Y_PX - EVENT_CONNECTOR_GAP_PX - EVENT_CARD_HEIGHT_PX - stackIndex * EVENT_STACK_GAP_PX
          : AXIS_Y_PX + EVENT_CONNECTOR_GAP_PX + stackIndex * EVENT_STACK_GAP_PX;
      const connectorPx = side === "above" ? AXIS_Y_PX - (topPx + EVENT_CARD_HEIGHT_PX) : topPx - AXIS_Y_PX;

      return {
        event,
        leftPct: getDatePercent(eventDate, startDate, endDate),
        side,
        topPx,
        connectorPx,
      };
    }),
  );
}

/**
 * 渲染 Outlook 横向时间轴画布。
 * @param props 事件、时间范围、工具栏与事件选择回调。
 * @returns 可交互的时间轴画布组件。
 */
export function EventTimelineCanvas({
  events,
  startDate,
  endDate,
  toolbar,
  onSelectEvent,
  onRangeChange,
}: EventTimelineCanvasProps) {
  const [selection, setSelection] = useState<DragSelection | null>(null);
  const safeStartDate = parseIsoDate(startDate) ?? new Date();
  const parsedEndDate = parseIsoDate(endDate);
  const safeEndDate = parsedEndDate && parsedEndDate > safeStartDate ? parsedEndDate : addFallbackYear(safeStartDate);
  const ticks = buildTimelineTicks(safeStartDate, safeEndDate);
  const positionedEvents = positionTimelineEvents(events, safeStartDate, safeEndDate);

  /**
   * 开始在画布中框选缩放区域。
   * @param event 指针按下事件。
   * @returns 无返回值。
   */
  function handleMouseDown(event: ReactMouseEvent<HTMLDivElement>) {
    if (event.button && event.button !== 0) return;
    if ((event.target as HTMLElement).closest("button")) return;
    const startX = getTrackX(event.clientX, event.currentTarget);
    setSelection({ startX, currentX: startX });
  }

  /**
   * 更新框选区域的当前位置。
   * @param event 指针移动事件。
   * @returns 无返回值。
   */
  function handleMouseMove(event: ReactMouseEvent<HTMLDivElement>) {
    if (!selection) return;
    if (event.buttons !== 1) return;
    const currentX = getTrackX(event.clientX, event.currentTarget);
    setSelection((current) => (current ? { ...current, currentX } : current));
  }

  /**
   * 完成框选并将选区转换成新的日期范围。
   * @param event 指针释放事件。
   * @returns 无返回值。
   */
  function handleMouseUp(event: ReactMouseEvent<HTMLDivElement>) {
    if (!selection) return;
    const track = event.currentTarget;
    const leftX = Math.min(selection.startX, selection.currentX);
    const rightX = Math.max(selection.startX, selection.currentX);
    setSelection(null);
    if (rightX - leftX < 24) return;

    const rect = track.getBoundingClientRect();
    const nextStartDate = getDateFromClientX(rect.left + leftX, track, safeStartDate, safeEndDate);
    const nextEndDate = getDateFromClientX(rect.left + rightX, track, safeStartDate, safeEndDate);
    if (!isUsableRange(nextStartDate, nextEndDate)) return;
    onRangeChange(toLocalIsoDate(nextStartDate), toLocalIsoDate(nextEndDate));
  }

  /**
   * 按鼠标滚轮位置进行中心缩放。
   * @param event 滚轮事件。
   * @returns 无返回值。
   */
  function handleWheel(event: ReactWheelEvent<HTMLDivElement>) {
    event.preventDefault();
    const currentSpanDays = (safeEndDate.getTime() - safeStartDate.getTime()) / (24 * 60 * 60 * 1000);
    const nextSpanDays = Math.min(MAX_ZOOM_DAYS, Math.max(MIN_ZOOM_DAYS, currentSpanDays * (event.deltaY < 0 ? 0.8 : 1.25)));
    if (Math.abs(nextSpanDays - currentSpanDays) < 0.5) return;

    const rect = event.currentTarget.getBoundingClientRect();
    const cursorRatio = clampInteractionRatio((event.clientX - rect.left) / Math.max(1, rect.width));
    const cursorDate = getDateFromClientX(event.clientX, event.currentTarget, safeStartDate, safeEndDate);
    const nextStartDate = addDays(cursorDate, -nextSpanDays * cursorRatio);
    const nextEndDate = addDays(nextStartDate, nextSpanDays);
    onRangeChange(toLocalIsoDate(nextStartDate), toLocalIsoDate(nextEndDate));
  }

  const selectionStyle = selection
    ? {
        left: Math.min(selection.startX, selection.currentX),
        width: Math.abs(selection.currentX - selection.startX),
      }
    : undefined;

  return (
    <section className="event-outlook-canvas" data-testid="event-timeline-canvas">
      <div className="event-outlook-canvas__toolbar">{toolbar}</div>
      <div
        aria-label={`事件时间轴，范围 ${startDate} 至 ${endDate}`}
        className="event-outlook-track"
        data-testid="event-timeline-track"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
        role="img"
        style={{ minHeight: TRACK_HEIGHT_PX }}
      >
        <div aria-hidden="true" className="event-outlook-axis" />
        {ticks.map((tick) => (
          <div aria-hidden="true" className="event-outlook-tick" key={tick.id} style={{ left: `${tick.leftPct}%` }}>
            <span>{tick.label}</span>
          </div>
        ))}

        {positionedEvents.map(({ event, leftPct, side, topPx, connectorPx }) => {
          const style: EventNodeStyle = {
            left: `${leftPct}%`,
            top: topPx,
            "--connector-height": `${connectorPx}px`,
          };

          return (
            <button
              aria-label={`编辑 ${event.title}`}
              className={`event-outlook-node event-outlook-node--${side} event-outlook-node--${event.category}`}
              key={event.id}
              onClick={() => onSelectEvent(event)}
              style={style}
              title={event.summary}
              type="button"
            >
              <span className="event-outlook-node__title">{event.title}</span>
              <span className="event-outlook-node__date">{event.event_date}</span>
              <span className="event-outlook-node__tooltip" role="tooltip">
                {event.summary}
              </span>
            </button>
          );
        })}
        {selection ? <div aria-hidden="true" className="event-outlook-selection" style={selectionStyle} /> : null}
      </div>
    </section>
  );
}
