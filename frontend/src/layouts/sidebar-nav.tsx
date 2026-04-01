import { useEffect, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { dashboardNavItem, moduleDirectories, primaryNavItems, secondaryNavItems } from "../shared/config/nav-items";
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

function itemInitials(title: string): string {
  const words = title.split(" ").filter(Boolean);

  if (words.length === 0) {
    return "?";
  }

  if (words.length === 1) {
    return words[0].slice(0, 2).toUpperCase();
  }

  return `${words[0][0]}${words[1][0]}`.toUpperCase();
}

function SidebarToggleIcon({ collapsed }: { collapsed: boolean }) {
  return (
    <svg aria-hidden="true" className="h-4 w-4" viewBox="0 0 16 16" fill="none">
      <rect x="1.5" y="2" width="13" height="12" rx="2.5" className="stroke-slate-500" strokeWidth="1.2" />
      <line x1="7.75" y1="2.8" x2="7.75" y2="13.2" className="stroke-slate-400" strokeWidth="1.2" />
      <rect x={collapsed ? "8.1" : "2.1"} y="2.6" width="5.1" height="10.8" rx="1.6" className="fill-slate-300" />
    </svg>
  );
}

function CompactNavSection({
  items,
  pathname,
  searchParams,
}: {
  items: NavItem[];
  pathname: string;
  searchParams: URLSearchParams;
}) {
  return (
    <div className="space-y-2">
      {items.map((item) => {
        const active = isNavTargetActive(item.to, pathname, searchParams);

        return (
          <Link
            key={item.to}
            aria-current={active ? "page" : undefined}
            aria-label={item.ariaLabel ?? item.title}
            title={item.title}
            to={buildNavHref(item.to, searchParams)}
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-lg border text-xs font-semibold transition",
              active
                ? "border-slate-300 bg-slate-200 text-slate-900"
                : "border-transparent text-slate-600 hover:bg-slate-100 hover:text-slate-900",
            )}
          >
            <span aria-hidden="true">{itemInitials(item.title)}</span>
          </Link>
        );
      })}
    </div>
  );
}

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
        "block rounded-xl border px-3 py-3 transition",
        active
          ? "border-slate-300 bg-slate-200 text-slate-900"
          : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:text-slate-950",
      )}
      to={buildNavHref(item.to, searchParams)}
    >
      <div className="font-semibold">{item.title}</div>
      <div aria-hidden="true" className="mt-1 text-xs opacity-80">
        {item.description}
      </div>
    </Link>
  );
}

function ExpandedModuleDirectories({
  directories,
  expandedByDirectory,
  onToggleDirectory,
  pathname,
  searchParams,
}: {
  directories: ModuleDirectory[];
  expandedByDirectory: Record<string, boolean>;
  onToggleDirectory: (id: string) => void;
  pathname: string;
  searchParams: URLSearchParams;
}) {
  return (
    <div className="space-y-2">
      {directories.map((directory) => {
        const expanded = expandedByDirectory[directory.id] ?? Boolean(directory.defaultExpanded);
        const childActive = directory.children.some((child) => isNavTargetActive(child.to, pathname, searchParams));
        const parentActive = !childActive && isNavTargetActive(directory.item.to, pathname, searchParams);

        return (
          <section key={directory.id} className="rounded-xl border border-slate-200 bg-slate-50/70 p-2">
            <div className="flex items-start gap-2">
              <Link
                aria-current={parentActive ? "page" : undefined}
                aria-label={directory.item.ariaLabel ?? directory.item.title}
                className={cn(
                  "flex-1 rounded-lg px-2 py-2 text-left transition",
                  parentActive
                    ? "bg-slate-200 text-slate-900"
                    : "text-slate-700 hover:bg-white hover:text-slate-950",
                )}
                to={buildNavHref(directory.item.to, searchParams)}
              >
                <div className="font-semibold">{directory.item.title}</div>
                <div aria-hidden="true" className="mt-1 text-xs opacity-80">
                  {directory.item.description}
                </div>
              </Link>
              <button
                aria-expanded={expanded}
                aria-label={expanded ? `Collapse ${directory.item.title} directory` : `Expand ${directory.item.title} directory`}
                className="mt-1 inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 bg-white text-sm text-slate-600 hover:border-slate-300 hover:text-slate-900"
                onClick={() => onToggleDirectory(directory.id)}
                type="button"
              >
                {expanded ? "-" : "+"}
              </button>
            </div>

            {expanded ? (
              <div className="mt-2 space-y-1 border-l border-slate-200 pl-3">
                {directory.children.map((child) => {
                  const active = isNavTargetActive(child.to, pathname, searchParams);

                  return (
                    <Link
                      key={child.to}
                      aria-current={active ? "page" : undefined}
                      aria-label={child.ariaLabel ?? child.title}
                      className={cn(
                        "block rounded-md px-2 py-1.5 text-sm transition",
                        active
                          ? "border border-slate-300 bg-slate-200 text-slate-900"
                          : "text-slate-600 hover:bg-white hover:text-slate-900",
                      )}
                      to={buildNavHref(child.to, searchParams)}
                    >
                      {child.title}
                    </Link>
                  );
                })}
              </div>
            ) : null}
          </section>
        );
      })}
    </div>
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
    <div className="space-y-1 rounded-xl border border-slate-200 bg-slate-50/70 p-2">
      <p className="px-2 pb-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">System</p>
      {secondaryNavItems.map((item) => {
        const active = isNavTargetActive(item.to, pathname, searchParams);

        return (
          <Link
            key={item.to}
            aria-current={active ? "page" : undefined}
            aria-label={item.ariaLabel ?? item.title}
            className={cn(
              "block rounded-lg px-3 py-2 text-sm transition",
              active ? "border border-slate-300 bg-slate-200 text-slate-900" : "text-slate-600 hover:bg-white hover:text-slate-900",
            )}
            to={buildNavHref(item.to, searchParams)}
          >
            <div className="font-medium">{item.title}</div>
            <div aria-hidden="true" className="mt-1 text-xs opacity-75">
              {item.description}
            </div>
          </Link>
        );
      })}
    </div>
  );
}

export function SidebarNav({ collapsed, onToggleCollapsed }: SidebarNavProps) {
  const { pathname } = useLocation();
  const [searchParams] = useSearchParams();
  const [expandedByDirectory, setExpandedByDirectory] = useState<Record<string, boolean>>(() => readStoredDirectoryState());

  useEffect(() => {
    window.localStorage.setItem(DIRECTORY_STATE_STORAGE_KEY, JSON.stringify(expandedByDirectory));
  }, [expandedByDirectory]);

  function toggleDirectory(id: string) {
    setExpandedByDirectory((prev) => ({
      ...prev,
      [id]: !(prev[id] ?? false),
    }));
  }

  return (
    <nav aria-label="Primary" className="flex h-full min-h-0 flex-col">
      <div className={cn("min-h-0 flex-1 overflow-y-auto", collapsed ? "pr-0" : "pr-1")}>
        <div className={cn("mb-5", collapsed ? "space-y-3" : "mb-6")}>
          <div className={cn("flex items-center", collapsed ? "justify-center" : "justify-between")}>
            {!collapsed ? <h1 className="text-xl font-semibold text-slate-950">Trend Insight</h1> : null}
            <button
              type="button"
              onClick={onToggleCollapsed}
              className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              <SidebarToggleIcon collapsed={collapsed} />
            </button>
          </div>

          {collapsed ? (
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-[0.14em] text-slate-700">
              TI
            </div>
          ) : null}
        </div>

        {collapsed ? (
          <CompactNavSection items={primaryNavItems} pathname={pathname} searchParams={searchParams} />
        ) : (
          <div className="space-y-2">
            <ExpandedSingleNavItem item={dashboardNavItem} pathname={pathname} searchParams={searchParams} />
            <ExpandedModuleDirectories
              directories={moduleDirectories}
              expandedByDirectory={expandedByDirectory}
              onToggleDirectory={toggleDirectory}
              pathname={pathname}
              searchParams={searchParams}
            />
          </div>
        )}
      </div>

      <div className={cn("pt-3", collapsed ? "border-t border-transparent" : "border-t border-slate-200")}>
        {collapsed ? (
          <CompactNavSection items={secondaryNavItems} pathname={pathname} searchParams={searchParams} />
        ) : (
          <ExpandedSystemLinks pathname={pathname} searchParams={searchParams} />
        )}
      </div>
    </nav>
  );
}
