import { Link } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  useSortable,
  horizontalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Bars3Icon } from "@heroicons/react/24/outline";
import { buildModuleTabHref, type ModuleTabDefinition } from "../lib/module-tabs";

type ModuleTabBarProps<TValue extends string> = {
  pathname: string;
  searchParams: URLSearchParams;
  tabs: readonly ModuleTabDefinition<TValue>[];
  activeTab: TValue;
  ariaLabel?: string;
  storageKey?: string;
};

function readStoredOrder(key: string, defaultValues: string[]): string[] {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return defaultValues;
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return defaultValues;
    const valid = parsed.filter((v): v is string => typeof v === "string");
    const defaultSet = new Set(defaultValues);
    const filtered = valid.filter((v) => defaultSet.has(v));
    for (const v of defaultValues) {
      if (!filtered.includes(v)) filtered.push(v);
    }
    return filtered;
  } catch {
    return defaultValues;
  }
}

function SortableTab<TValue extends string>({
  tab,
  selected,
  pathname,
  searchParams,
}: {
  tab: ModuleTabDefinition<TValue>;
  selected: boolean;
  pathname: string;
  searchParams: URLSearchParams;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: tab.value });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} className="flex items-center gap-0.5">
      <Link
        aria-current={selected ? "page" : undefined}
        className={[
          "inline-flex items-center rounded-full border px-4 py-2 text-sm font-medium transition",
          selected
            ? "border-slate-900 bg-slate-900 text-white shadow-sm"
            : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-950",
        ].join(" ")}
        to={buildModuleTabHref(pathname, searchParams, tab.value)}
      >
        {tab.label}
      </Link>
      <button
        type="button"
        {...attributes}
        {...listeners}
        className="inline-flex h-6 w-4 items-center justify-center rounded text-slate-300 hover:text-slate-500 cursor-grab active:cursor-grabbing flex-shrink-0"
        aria-label={`拖拽排序 ${tab.label}`}
      >
        <Bars3Icon aria-hidden="true" className="h-3 w-3" />
      </button>
    </div>
  );
}

export function ModuleTabBar<TValue extends string>({
  pathname,
  searchParams,
  tabs,
  activeTab,
  ariaLabel = "Module tabs",
  storageKey,
}: ModuleTabBarProps<TValue>) {
  const defaultOrder = useMemo(() => tabs.map((t) => t.value), [tabs]);
  const key = storageKey ?? `tab-order-${pathname}`;

  const [order, setOrder] = useState<string[]>(() => readStoredOrder(key, defaultOrder));

  useEffect(() => {
    window.localStorage.setItem(key, JSON.stringify(order));
  }, [key, order]);

  useEffect(() => {
    const currentValues = new Set(tabs.map((t) => t.value));
    const storedSet = new Set(order);
    if (currentValues.size !== storedSet.size || ![...currentValues].every((v) => storedSet.has(v))) {
      const newDefaults = tabs.map((t) => t.value);
      setOrder(readStoredOrder(key, newDefaults));
    }
  }, [tabs]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
  );

  const orderedTabs = useMemo(() => {
    const map = new Map(tabs.map((t) => [t.value, t]));
    return order.map((v) => map.get(v as TValue)).filter((t): t is ModuleTabDefinition<TValue> => t !== undefined);
  }, [tabs, order]);

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = order.indexOf(active.id as string);
    const newIndex = order.indexOf(over.id as string);
    if (oldIndex !== -1 && newIndex !== -1) {
      setOrder(arrayMove(order, oldIndex, newIndex));
    }
  }

  return (
    <nav aria-label={ariaLabel}>
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={order} strategy={horizontalListSortingStrategy}>
          <div className="flex flex-wrap gap-2">
            {orderedTabs.map((tab) => {
              const selected = tab.value === activeTab;
              return (
                <SortableTab
                  key={tab.value}
                  tab={tab}
                  selected={selected}
                  pathname={pathname}
                  searchParams={searchParams}
                />
              );
            })}
          </div>
        </SortableContext>
      </DndContext>
    </nav>
  );
}
