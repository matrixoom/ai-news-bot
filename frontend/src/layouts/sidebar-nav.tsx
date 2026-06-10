import {
  Bars3Icon,
  CalendarDaysIcon,
  ChartBarSquareIcon,
  ChartPieIcon,
  CheckIcon,
  ChevronDownIcon,
  ChevronDoubleLeftIcon,
  ChevronDoubleRightIcon,
  ChevronUpIcon,
  Cog6ToothIcon,
  CpuChipIcon,
  DocumentTextIcon,
  PaperAirplaneIcon,
  PencilSquareIcon,
  SparklesIcon,
} from "@heroicons/react/24/outline";
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
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { moduleDirectories, primaryNavItems, secondaryNavItems } from "../shared/config/nav-items";
import { cn } from "../shared/lib/cn";
import type { ModuleDirectory, NavItem } from "../shared/config/nav-items";

type SidebarNavProps = {
  collapsed: boolean;
  onToggleCollapsed: () => void;
};

type ParsedTarget = {
  pathname: string;
  params: URLSearchParams;
};

const DIRECTORY_STATE_STORAGE_KEY = "dashboard-directory-expanded";
const DIRECTORY_ORDER_KEY = "sidebar-directory-order";
const CHILD_ORDER_PREFIX = "sidebar-child-order-";
const PRIMARY_NAV_ORDER_KEY = "sidebar-primary-nav-order";

// ── localStorage helpers ──

function readStoredOrder(key: string, defaultIds: string[]): string[] {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return defaultIds;
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return defaultIds;
    const valid = parsed.filter((id): id is string => typeof id === "string");
    const defaultSet = new Set(defaultIds);
    const filtered = valid.filter((id) => defaultSet.has(id));
    for (const id of defaultIds) {
      if (!filtered.includes(id)) filtered.push(id);
    }
    return filtered;
  } catch {
    return defaultIds;
  }
}

function writeStoredOrder(key: string, ids: string[]) {
  window.localStorage.setItem(key, JSON.stringify(ids));
}

function getDefaultDirectoryState(): Record<string, boolean> {
  return Object.fromEntries(moduleDirectories.map((directory) => [directory.id, directory.defaultExpanded ?? false]));
}

function readStoredDirectoryState(): Record<string, boolean> {
  const defaults = getDefaultDirectoryState();
  const rawValue = window.localStorage.getItem(DIRECTORY_STATE_STORAGE_KEY);

  if (!rawValue) {
    return defaults;
  }

  try {
    const parsed = JSON.parse(rawValue) as Record<string, unknown>;

    return Object.fromEntries(
      moduleDirectories.map((directory) => {
        const nextValue = parsed[directory.id];
        return [directory.id, typeof nextValue === "boolean" ? nextValue : (directory.defaultExpanded ?? false)];
      }),
    );
  } catch {
    return defaults;
  }
}

function parseTarget(target: string): ParsedTarget {
  const [pathname, query = ""] = target.split("?");
  return { pathname, params: new URLSearchParams(query) };
}

function buildNavHref(target: string, currentSearchParams: URLSearchParams): string {
  const { pathname, params } = parseTarget(target);
  const nextSearchParams = new URLSearchParams(params);
  const newsMode = currentSearchParams.get("news_mode");

  if (newsMode) {
    nextSearchParams.set("news_mode", newsMode);
  }

  const query = nextSearchParams.toString();
  return query ? `${pathname}?${query}` : pathname;
}

function isNavTargetActive(target: string, pathname: string, currentSearchParams: URLSearchParams): boolean {
  const { pathname: targetPathname, params } = parseTarget(target);

  if (pathname !== targetPathname) {
    return false;
  }

  for (const [key, value] of params.entries()) {
    if (currentSearchParams.get(key) !== value) {
      return false;
    }
  }

  return true;
}

/** 展示侧栏展开/收起按钮图标；参数 collapsed 表示当前是否折叠，返回对应的 Heroicons 图标。 */
function SidebarToggleIcon({ collapsed }: { collapsed: boolean }) {
  const Icon = collapsed ? ChevronDoubleRightIcon : ChevronDoubleLeftIcon;

  return <Icon aria-hidden="true" className="h-4 w-4" />;
}

/** 根据导航目标选择折叠态图标；参数 item 为导航配置，返回对应的 Heroicons 装饰图标。 */
function CompactNavIcon({ item }: { item: NavItem }) {
  const { pathname } = parseTarget(item.to);
  const iconClassName = "h-5 w-5";

  if (pathname === "/settings") {
    return <Cog6ToothIcon aria-hidden="true" className={iconClassName} />;
  }

  if (pathname === "/macro-data") {
    return <ChartBarSquareIcon aria-hidden="true" className={iconClassName} />;
  }

  if (pathname === "/market-data") {
    return <ChartPieIcon aria-hidden="true" className={iconClassName} />;
  }

  if (pathname === "/event-outlook") {
    return <CalendarDaysIcon aria-hidden="true" className={iconClassName} />;
  }

  if (pathname === "/notes") {
    return <DocumentTextIcon aria-hidden="true" className={iconClassName} />;
  }

  if (pathname === "/trend-models") {
    return <SparklesIcon aria-hidden="true" className={iconClassName} />;
  }

  if (pathname === "/ai-agent") {
    return <CpuChipIcon aria-hidden="true" className={iconClassName} />;
  }

  return <PaperAirplaneIcon aria-hidden="true" className={iconClassName} />;
}

// ── sortable primitives ──

function SortableDirectorySection({
  directory,
  expanded,
  onToggleDirectory,
  pathname,
  searchParams,
  childOrder,
  onChildOrderChange,
  editing,
}: {
  directory: ModuleDirectory;
  expanded: boolean;
  onToggleDirectory: (id: string) => void;
  pathname: string;
  searchParams: URLSearchParams;
  childOrder: string[];
  onChildOrderChange: (newOrder: string[]) => void;
  editing: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: directory.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const hasChildren = directory.children.length > 0;
  const childActive = directory.children.some((child) => isNavTargetActive(child.to, pathname, searchParams));
  const parentActive = !childActive && isNavTargetActive(directory.item.to, pathname, searchParams);

  const childSensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
  );

  const orderedChildren = useMemo(() => {
    const map = new Map(directory.children.map((c) => [c.to, c]));
    return childOrder.map((to) => map.get(to)).filter((c): c is NavItem => c !== undefined);
  }, [directory.children, childOrder]);

  function handleChildDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = childOrder.indexOf(active.id as string);
    const newIndex = childOrder.indexOf(over.id as string);
    if (oldIndex !== -1 && newIndex !== -1) {
      const nextOrder = arrayMove(childOrder, oldIndex, newIndex);
      onChildOrderChange(nextOrder);
    }
  }

  return (
    <section ref={setNodeRef} style={style} className="border-b border-line py-1">
      <div className="flex items-start gap-1">
        {editing ? (
          <button
            type="button"
            {...attributes}
            {...listeners}
            className="mt-1 inline-flex h-8 w-6 cursor-grab items-center justify-center rounded text-muted hover:text-ink active:cursor-grabbing"
            aria-label={`拖拽排序 ${directory.item.title}`}
          >
            <Bars3Icon aria-hidden="true" className="h-4 w-4" />
          </button>
        ) : null}
        <Link
          aria-current={parentActive ? "page" : undefined}
          aria-label={directory.item.ariaLabel ?? directory.item.title}
          className={cn(
            "relative flex-1 rounded-control px-3 py-2 text-left",
            parentActive
              ? "bg-accent-soft text-accent before:absolute before:inset-y-2 before:left-0 before:w-0.5 before:rounded-full before:bg-accent"
              : "text-ink hover:bg-surface-subtle",
          )}
          to={buildNavHref(directory.item.to, searchParams)}
        >
          <div className="font-semibold">{directory.item.title}</div>
        </Link>
        {hasChildren ? (
          <button
            aria-expanded={expanded}
            aria-label={expanded ? `Collapse ${directory.item.title} directory` : `Expand ${directory.item.title} directory`}
            className="mt-1 inline-flex h-8 w-8 items-center justify-center rounded-control text-muted hover:bg-surface-subtle hover:text-ink"
            onClick={() => onToggleDirectory(directory.id)}
            type="button"
          >
            {expanded ? (
              <ChevronUpIcon aria-hidden="true" className="h-4 w-4" />
            ) : (
              <ChevronDownIcon aria-hidden="true" className="h-4 w-4" />
            )}
          </button>
        ) : null}
      </div>

      {hasChildren && expanded ? (
        <DndContext sensors={childSensors} collisionDetection={closestCenter} onDragEnd={handleChildDragEnd}>
          <SortableContext items={childOrder} strategy={verticalListSortingStrategy}>
            <div className="mb-1 mt-1 space-y-0.5 border-l border-line pl-3">
              {orderedChildren.map((child) => (
                <SortableChildLink
                  key={child.to}
                  child={child}
                  pathname={pathname}
                  searchParams={searchParams}
                  editing={editing}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      ) : null}
    </section>
  );
}

function SortableChildLink({
  child,
  pathname,
  searchParams,
  editing,
}: {
  child: NavItem;
  pathname: string;
  searchParams: URLSearchParams;
  editing: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: child.to });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  const active = isNavTargetActive(child.to, pathname, searchParams);

  return (
    <div ref={setNodeRef} style={style} className="flex items-center gap-1">
      {editing ? (
        <button
          type="button"
          {...attributes}
          {...listeners}
          className="inline-flex h-6 w-4 cursor-grab items-center justify-center rounded text-muted hover:text-ink active:cursor-grabbing"
          aria-label={`拖拽排序 ${child.title}`}
        >
          <Bars3Icon aria-hidden="true" className="h-3 w-3" />
        </button>
      ) : null}
      <Link
        aria-current={active ? "page" : undefined}
        aria-label={child.ariaLabel ?? child.title}
        className={cn(
          "relative flex-1 rounded-control px-3 py-1.5 text-sm",
          active
            ? "bg-accent-soft font-medium text-accent before:absolute before:inset-y-1.5 before:-left-[13px] before:w-0.5 before:bg-accent"
            : "text-muted hover:bg-surface-subtle hover:text-ink",
        )}
        to={buildNavHref(child.to, searchParams)}
      >
        {child.title}
      </Link>
    </div>
  );
}

// ── compact nav ──

function SortableCompactItem({
  item,
  pathname,
  searchParams,
  editing,
}: {
  item: NavItem;
  pathname: string;
  searchParams: URLSearchParams;
  editing: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: item.to });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  const active = isNavTargetActive(item.to, pathname, searchParams);

  return (
    <div ref={setNodeRef} style={style} className="flex items-center gap-1">
      <Link
        aria-current={active ? "page" : undefined}
        aria-label={item.ariaLabel ?? item.title}
        title={item.title}
        to={buildNavHref(item.to, searchParams)}
        className={cn(
          "flex h-10 w-10 items-center justify-center rounded-control border text-xs font-semibold",
          active
            ? "border-accent/20 bg-accent-soft text-accent"
            : "border-transparent text-muted hover:bg-surface-subtle hover:text-ink",
        )}
      >
        <CompactNavIcon item={item} />
      </Link>
      {editing ? (
        <button
          type="button"
          {...attributes}
          {...listeners}
          className="inline-flex h-6 w-4 cursor-grab items-center justify-center rounded text-muted hover:text-ink active:cursor-grabbing"
          aria-label={`拖拽排序 ${item.title}`}
        >
          <Bars3Icon aria-hidden="true" className="h-3 w-3" />
        </button>
      ) : null}
    </div>
  );
}

function CompactNavSection({
  items,
  pathname,
  searchParams,
  navOrder,
  onNavOrderChange,
  editing,
}: {
  items: NavItem[];
  pathname: string;
  searchParams: URLSearchParams;
  navOrder: string[];
  onNavOrderChange: (newOrder: string[]) => void;
  editing: boolean;
}) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
  );

  const orderedItems = useMemo(() => {
    const map = new Map(items.map((item) => [item.to, item]));
    return navOrder.map((to) => map.get(to)).filter((item): item is NavItem => item !== undefined);
  }, [items, navOrder]);

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = navOrder.indexOf(active.id as string);
    const newIndex = navOrder.indexOf(over.id as string);
    if (oldIndex !== -1 && newIndex !== -1) {
      onNavOrderChange(arrayMove(navOrder, oldIndex, newIndex));
    }
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={navOrder} strategy={verticalListSortingStrategy}>
        <div className="space-y-2">
          {orderedItems.map((item) => (
            <SortableCompactItem
              key={item.to}
              item={item}
              pathname={pathname}
              searchParams={searchParams}
              editing={editing}
            />
          ))}
        </div>
      </SortableContext>
    </DndContext>
  );
}

// ── expanded nav ──

function ExpandedSingleNavItem({
  item,
  pathname,
  searchParams,
}: {
  item: NavItem;
  pathname: string;
  searchParams: URLSearchParams;
}) {
  const active = isNavTargetActive(item.to, pathname, searchParams);

  return (
    <Link
      aria-current={active ? "page" : undefined}
      aria-label={item.ariaLabel ?? item.title}
      className={cn(
        "relative block rounded-control px-3 py-2.5",
        active
          ? "bg-accent-soft text-accent before:absolute before:inset-y-2 before:left-0 before:w-0.5 before:rounded-full before:bg-accent"
          : "text-ink hover:bg-surface-subtle",
      )}
      to={buildNavHref(item.to, searchParams)}
    >
      <div className="font-semibold">{item.title}</div>
    </Link>
  );
}

function ExpandedModuleDirectories({
  directories,
  expandedByDirectory,
  onToggleDirectory,
  pathname,
  searchParams,
  directoryOrder,
  childOrders,
  onDirectoryOrderChange,
  onChildOrderChange,
  editing,
}: {
  directories: ModuleDirectory[];
  expandedByDirectory: Record<string, boolean>;
  onToggleDirectory: (id: string) => void;
  pathname: string;
  searchParams: URLSearchParams;
  directoryOrder: string[];
  childOrders: Record<string, string[]>;
  onDirectoryOrderChange: (newOrder: string[]) => void;
  onChildOrderChange: (directoryId: string, newOrder: string[]) => void;
  editing: boolean;
}) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
  );

  const orderedDirectories = useMemo(() => {
    const map = new Map(directories.map((d) => [d.id, d]));
    return directoryOrder.map((id) => map.get(id)).filter((d): d is ModuleDirectory => d !== undefined);
  }, [directories, directoryOrder]);

  function handleDirectoryDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = directoryOrder.indexOf(active.id as string);
    const newIndex = directoryOrder.indexOf(over.id as string);
    if (oldIndex !== -1 && newIndex !== -1) {
      onDirectoryOrderChange(arrayMove(directoryOrder, oldIndex, newIndex));
    }
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDirectoryDragEnd}>
      <SortableContext items={directoryOrder} strategy={verticalListSortingStrategy}>
        <div className="space-y-2">
          {orderedDirectories.map((directory) => {
            const expanded = expandedByDirectory[directory.id] ?? Boolean(directory.defaultExpanded);
            const childOrder = childOrders[directory.id] ?? directory.children.map((c) => c.to);

            return (
              <SortableDirectorySection
                key={directory.id}
                childOrder={childOrder}
                directory={directory}
                expanded={expanded}
                onChildOrderChange={(newOrder) => onChildOrderChange(directory.id, newOrder)}
                onToggleDirectory={onToggleDirectory}
                pathname={pathname}
                searchParams={searchParams}
                editing={editing}
              />
            );
          })}
        </div>
      </SortableContext>
    </DndContext>
  );
}

function ExpandedSystemLinks({
  pathname,
  searchParams,
}: {
  pathname: string;
  searchParams: URLSearchParams;
}) {
  return (
    <div className="space-y-1 pt-2">
      <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">System</p>
      {secondaryNavItems.map((item) => {
        const active = isNavTargetActive(item.to, pathname, searchParams);

        return (
          <Link
            key={item.to}
            aria-current={active ? "page" : undefined}
            aria-label={item.ariaLabel ?? item.title}
            className={cn(
              "relative block rounded-control px-3 py-2 text-sm",
              active
                ? "bg-accent-soft text-accent before:absolute before:inset-y-2 before:left-0 before:w-0.5 before:bg-accent"
                : "text-muted hover:bg-surface-subtle hover:text-ink",
            )}
            to={buildNavHref(item.to, searchParams)}
          >
            <div className="font-medium">{item.title}</div>
          </Link>
        );
      })}
    </div>
  );
}

// ── main ──

export function SidebarNav({ collapsed, onToggleCollapsed }: SidebarNavProps) {
  const { pathname } = useLocation();
  const [searchParams] = useSearchParams();
  const [expandedByDirectory, setExpandedByDirectory] = useState<Record<string, boolean>>(() => readStoredDirectoryState());

  const [directoryOrder, setDirectoryOrder] = useState<string[]>(() =>
    readStoredOrder(DIRECTORY_ORDER_KEY, moduleDirectories.map((d) => d.id)),
  );
  const [childOrders, setChildOrders] = useState<Record<string, string[]>>(() => {
    const result: Record<string, string[]> = {};
    for (const d of moduleDirectories) {
      result[d.id] = readStoredOrder(`${CHILD_ORDER_PREFIX}${d.id}`, d.children.map((c) => c.to));
    }
    return result;
  });
  const [primaryNavOrder, setPrimaryNavOrder] = useState<string[]>(() =>
    readStoredOrder(PRIMARY_NAV_ORDER_KEY, primaryNavItems.map((n) => n.to)),
  );
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    window.localStorage.setItem(DIRECTORY_STATE_STORAGE_KEY, JSON.stringify(expandedByDirectory));
  }, [expandedByDirectory]);

  useEffect(() => {
    writeStoredOrder(DIRECTORY_ORDER_KEY, directoryOrder);
  }, [directoryOrder]);

  useEffect(() => {
    for (const [dirId, order] of Object.entries(childOrders)) {
      writeStoredOrder(`${CHILD_ORDER_PREFIX}${dirId}`, order);
    }
  }, [childOrders]);

  useEffect(() => {
    writeStoredOrder(PRIMARY_NAV_ORDER_KEY, primaryNavOrder);
  }, [primaryNavOrder]);

  function toggleDirectory(id: string) {
    setExpandedByDirectory((prev) => ({
      ...prev,
      [id]: !(prev[id] ?? false),
    }));
  }

  function handleChildOrderChange(directoryId: string, newOrder: string[]) {
    setChildOrders((prev) => ({ ...prev, [directoryId]: newOrder }));
  }

  return (
    <nav aria-label="Primary" className="flex h-full min-h-0 flex-col">
      <div className={cn("min-h-0 flex-1 overflow-y-auto", collapsed ? "pr-0" : "pr-1")}>
        <div className={cn("mb-5", collapsed ? "space-y-3" : "mb-6")}>
          <div className={cn("flex items-center", collapsed ? "justify-center" : "justify-between")}>
            {!collapsed ? (
              <div>
                <h1 className="text-base font-semibold tracking-tight text-ink">Trend Insight</h1>
                <p className="mt-0.5 text-[11px] text-muted">研究工作台</p>
              </div>
            ) : null}
            <button
              type="button"
              onClick={onToggleCollapsed}
              className="workbench-icon-button h-8 w-8"
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              <SidebarToggleIcon collapsed={collapsed} />
            </button>
          </div>
        </div>

        {collapsed ? (
          <CompactNavSection
            items={primaryNavItems}
            pathname={pathname}
            searchParams={searchParams}
            navOrder={primaryNavOrder}
            onNavOrderChange={setPrimaryNavOrder}
            editing={editing}
          />
        ) : (
          <div className="space-y-2">
            <ExpandedModuleDirectories
              childOrders={childOrders}
              directories={moduleDirectories}
              directoryOrder={directoryOrder}
              expandedByDirectory={expandedByDirectory}
              onChildOrderChange={handleChildOrderChange}
              onDirectoryOrderChange={setDirectoryOrder}
              onToggleDirectory={toggleDirectory}
              pathname={pathname}
              searchParams={searchParams}
              editing={editing}
            />
          </div>
        )}
      </div>

      <div className={cn("space-y-2 pt-3", collapsed ? "border-t border-transparent" : "border-t border-line")}>
        <button
          aria-label={editing ? "完成导航编辑" : "编辑导航"}
          className={cn(
            "flex items-center justify-center rounded-control text-xs font-medium",
            collapsed ? "h-9 w-10" : "h-9 w-full gap-2 px-3",
            editing ? "bg-accent-soft text-accent" : "text-muted hover:bg-surface-subtle hover:text-ink",
          )}
          onClick={() => setEditing((value) => !value)}
          type="button"
        >
          {editing ? (
            <CheckIcon aria-hidden="true" className="h-4 w-4" />
          ) : (
            <PencilSquareIcon aria-hidden="true" className="h-4 w-4" />
          )}
          {!collapsed ? <span>{editing ? "完成" : "编辑导航"}</span> : null}
        </button>
        {collapsed ? (
          <CompactNavSection
            items={secondaryNavItems}
            pathname={pathname}
            searchParams={searchParams}
            navOrder={secondaryNavItems.map((n) => n.to)}
            onNavOrderChange={() => {}}
            editing={false}
          />
        ) : (
          <ExpandedSystemLinks pathname={pathname} searchParams={searchParams} />
        )}
      </div>
    </nav>
  );
}
