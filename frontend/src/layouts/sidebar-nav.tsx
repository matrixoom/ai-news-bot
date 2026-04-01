import { useState } from "react";
import { NavLink, useSearchParams } from "react-router-dom";
import { primaryNavGroups, secondaryNavGroups } from "../shared/config/nav-items";
import { cn } from "../shared/lib/cn";
import type { NavGroup, NavItem } from "../shared/config/nav-items";

type SidebarNavProps = {
  collapsed: boolean;
  onToggleCollapsed: () => void;
};

function buildNavHref(pathname: string, searchParams: URLSearchParams): string {
  const nextSearchParams = new URLSearchParams();
  const newsMode = searchParams.get("news_mode");

  if (newsMode) {
    nextSearchParams.set("news_mode", newsMode);
  }

  const query = nextSearchParams.toString();
  return query ? `${pathname}?${query}` : pathname;
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

function CompactNavSection({ items }: { items: NavItem[] }) {
  const [searchParams] = useSearchParams();

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={buildNavHref(item.to, searchParams)}
          aria-label={item.title}
          title={item.title}
          className={({ isActive }) =>
            cn(
              "flex h-10 w-10 items-center justify-center rounded-lg text-xs font-semibold transition",
              isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
            )
          }
        >
          <span aria-hidden="true">{itemInitials(item.title)}</span>
        </NavLink>
      ))}
    </div>
  );
}

function GroupedNavSection({
  groups,
  expandedByGroup,
  onToggleGroup,
}: {
  groups: NavGroup[];
  expandedByGroup: Record<string, boolean>;
  onToggleGroup: (groupId: string) => void;
}) {
  const [searchParams] = useSearchParams();

  return (
    <div className="space-y-3">
      {groups.map((group) => {
        const isExpanded = expandedByGroup[group.id] ?? Boolean(group.defaultExpanded);
        const regionId = `${group.id}-items`;

        return (
          <section key={group.id} className="rounded-xl border border-slate-200 bg-slate-50/70 p-2">
            <button
              type="button"
              className="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left text-xs font-semibold uppercase tracking-[0.14em] text-slate-600 hover:bg-slate-100"
              aria-controls={regionId}
              aria-expanded={isExpanded}
              aria-label={isExpanded ? `Collapse ${group.title} section` : `Expand ${group.title} section`}
              onClick={() => onToggleGroup(group.id)}
            >
              <span>{group.title}</span>
              <span aria-hidden="true" className="text-sm tracking-normal">
                {isExpanded ? "-" : "+"}
              </span>
            </button>
            <p className="px-2 pb-1 text-[11px] text-slate-500">{group.description}</p>

            {isExpanded ? (
              <div id={regionId} className="space-y-1" role="group" aria-label={`${group.title} links`}>
                {group.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={buildNavHref(item.to, searchParams)}
                    aria-label={item.title}
                    className={({ isActive }) =>
                      cn(
                        "block rounded-lg px-3 py-2 text-sm transition",
                        isActive
                          ? "bg-slate-900 text-white"
                          : "text-slate-600 hover:bg-white hover:text-slate-900",
                      )
                    }
                  >
                    <div className="font-medium">{item.title}</div>
                    <div aria-hidden="true" className="mt-1 text-xs opacity-75">
                      {item.description}
                    </div>
                  </NavLink>
                ))}
              </div>
            ) : null}
          </section>
        );
      })}
    </div>
  );
}

export function SidebarNav({ collapsed, onToggleCollapsed }: SidebarNavProps) {
  const [expandedByGroup, setExpandedByGroup] = useState<Record<string, boolean>>(() => {
    const allGroups = [...primaryNavGroups, ...secondaryNavGroups];
    return Object.fromEntries(allGroups.map((group) => [group.id, group.defaultExpanded ?? true]));
  });

  function toggleGroup(groupId: string) {
    setExpandedByGroup((prev) => ({
      ...prev,
      [groupId]: !(prev[groupId] ?? true),
    }));
  }

  const primaryCompactItems = primaryNavGroups.flatMap((group) => group.items);
  const secondaryCompactItems = secondaryNavGroups.flatMap((group) => group.items);

  return (
    <nav aria-label="Primary" className="flex h-full flex-col justify-between">
      <div>
        <div className={cn("mb-5", collapsed ? "space-y-3" : "mb-8")}>
          <button
            type="button"
            onClick={onToggleCollapsed}
            className="inline-flex h-8 items-center rounded-md border border-slate-200 bg-white px-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600 hover:bg-slate-100"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? ">" : "<"}
          </button>

          {collapsed ? (
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-[0.14em] text-slate-700">
              RD
            </div>
          ) : (
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Research Desk</p>
              <h1 className="mt-2 text-xl font-semibold text-slate-950">Trend Insight</h1>
              <p className="mt-3 text-sm text-slate-600">Loading workspace...</p>
            </div>
          )}
        </div>

        {collapsed ? (
          <CompactNavSection items={primaryCompactItems} />
        ) : (
          <GroupedNavSection
            groups={primaryNavGroups}
            expandedByGroup={expandedByGroup}
            onToggleGroup={toggleGroup}
          />
        )}
      </div>

      {collapsed ? (
        <CompactNavSection items={secondaryCompactItems} />
      ) : (
        <GroupedNavSection
          groups={secondaryNavGroups}
          expandedByGroup={expandedByGroup}
          onToggleGroup={toggleGroup}
        />
      )}
    </nav>
  );
}
