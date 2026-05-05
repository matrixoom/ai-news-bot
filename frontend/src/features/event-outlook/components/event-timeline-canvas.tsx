import { useEffect, useMemo, useRef, useState } from "react";
import { DataSet } from "vis-data/peer";
import { Timeline, type TimelineOptions } from "vis-timeline/peer";
import "vis-timeline/styles/vis-timeline-graph2d.min.css";
import type { EventOutlookEvent, EventOutlookResolution } from "../model/event-outlook.types";

type EventTimelineCanvasProps = {
  events: EventOutlookEvent[];
  resolution: EventOutlookResolution;
  startDate: string;
  endDate: string;
  onSelectEvent: (event: EventOutlookEvent) => void;
  onRangeChange: (startDate: string, endDate: string) => void;
};

type DragSelection = {
  startX: number;
  currentX: number;
  top: number;
};

function resolutionZoomWindow(resolution: EventOutlookResolution): number {
  if (resolution === "day") return 1000 * 60 * 60 * 24 * 14;
  if (resolution === "week") return 1000 * 60 * 60 * 24 * 70;
  return 1000 * 60 * 60 * 24 * 210;
}

function toLocalIsoDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function parseIsoDate(value: string): Date | null {
  const parsed = new Date(`${value}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function EventTimelineCanvas({
  events,
  resolution,
  startDate,
  endDate,
  onSelectEvent,
  onRangeChange,
}: EventTimelineCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const timelineRef = useRef<Timeline | null>(null);
  const itemsRef = useRef<DataSet<any> | null>(null);
  const eventsRef = useRef(events);
  const [selection, setSelection] = useState<DragSelection | null>(null);

  useEffect(() => {
    eventsRef.current = events;
  }, [events]);

  const items = useMemo(
    () =>
      events.map((event, index) => ({
        id: event.id,
        content: event.title,
        start: event.event_date,
        type: "box",
        title: event.summary,
        className: `event-${event.category} ${index % 2 === 0 ? "event-above" : "event-below"}`,
      })),
    [events],
  );

  useEffect(() => {
    if (!containerRef.current) return;
    const dataSet = new DataSet(items);
    const safeStartDate = parseIsoDate(startDate) ?? new Date();
    const safeEndDate = parseIsoDate(endDate) ?? new Date(safeStartDate.getTime() + 1000 * 60 * 60 * 24 * 365);
    itemsRef.current = dataSet;
    const options: TimelineOptions = {
      width: "100%",
      minHeight: "420px",
      stack: true,
      horizontalScroll: true,
      verticalScroll: true,
      zoomable: true,
      moveable: true,
      preferZoom: true,
      selectable: true,
      showCurrentTime: true,
      orientation: { axis: "bottom", item: "top" },
      start: safeStartDate,
      end: safeEndDate,
      tooltip: { followMouse: true, overflowMethod: "cap" },
      zoomMin: 1000 * 60 * 60 * 24,
      zoomMax: 1000 * 60 * 60 * 24 * 370,
      margin: { item: { horizontal: 14, vertical: 12 }, axis: 24 },
    };
    const timeline = new Timeline(containerRef.current, dataSet, options);
    timelineRef.current = timeline;
    timeline.on("doubleClick", (properties) => {
      const eventId = Number(properties.item);
      const selected = eventsRef.current.find((event) => event.id === eventId);
      if (selected) onSelectEvent(selected);
    });

    return () => {
      timeline.destroy();
      timelineRef.current = null;
      itemsRef.current = null;
    };
  }, []);

  useEffect(() => {
    itemsRef.current?.clear();
    itemsRef.current?.add(items);
  }, [items]);

  useEffect(() => {
    const timeline = timelineRef.current;
    if (!timeline) return;
    const start = parseIsoDate(startDate);
    const end = parseIsoDate(endDate);
    if (!start || !end) return;
    const center = new Date((start.getTime() + end.getTime()) / 2);
    const span = resolutionZoomWindow(resolution);
    timeline.setWindow(new Date(center.getTime() - span / 2), new Date(center.getTime() + span / 2), {
      animation: { duration: 250, easingFunction: "easeInOutQuad" },
    });
  }, [resolution, startDate, endDate]);

  function handlePointerDown(event: React.PointerEvent<HTMLDivElement>) {
    if (!event.shiftKey) return;
    const rect = event.currentTarget.getBoundingClientRect();
    setSelection({
      startX: event.clientX - rect.left,
      currentX: event.clientX - rect.left,
      top: event.clientY - rect.top,
    });
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event: React.PointerEvent<HTMLDivElement>) {
    if (!selection) return;
    const rect = event.currentTarget.getBoundingClientRect();
    setSelection((current) => (current ? { ...current, currentX: event.clientX - rect.left } : current));
  }

  function handlePointerUp(event: React.PointerEvent<HTMLDivElement>) {
    const timeline = timelineRef.current;
    if (!selection || !timeline) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const left = Math.min(selection.startX, selection.currentX);
    const right = Math.max(selection.startX, selection.currentX);
    setSelection(null);
    if (right - left < 24) return;

    const startProps = timeline.getEventProperties({
      clientX: rect.left + left,
      clientY: rect.top + selection.top,
    } as MouseEvent);
    const endProps = timeline.getEventProperties({
      clientX: rect.left + right,
      clientY: rect.top + selection.top,
    } as MouseEvent);
    if (startProps.time && endProps.time) {
      const rangeStart = toLocalIsoDate(startProps.time);
      const rangeEnd = toLocalIsoDate(endProps.time);
      onRangeChange(rangeStart, rangeEnd);
      timeline.setWindow(startProps.time, endProps.time, { animation: true });
    }
  }

  const selectionStyle = selection
    ? {
        left: Math.min(selection.startX, selection.currentX),
        width: Math.abs(selection.currentX - selection.startX),
      }
    : undefined;

  return (
    <div
      className="relative overflow-hidden rounded-lg border border-slate-200 bg-white"
      data-testid="event-timeline-canvas"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
    >
      <div ref={containerRef} className="event-outlook-timeline min-h-[420px]" />
      {selection ? (
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-y-4 rounded border border-sky-400 bg-sky-100/30"
          style={selectionStyle}
        />
      ) : null}
    </div>
  );
}
