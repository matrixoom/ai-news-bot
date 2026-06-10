import { XMarkIcon } from "@heroicons/react/24/outline";
import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { useThemePreference } from "../shared/hooks/use-theme-preference";
import { useBooleanWorkbenchPreference } from "../shared/hooks/use-workbench-preference";
import { SIDEBAR_COLLAPSED_STORAGE_KEY } from "../shared/lib/workbench-preferences";
import { HeaderBar } from "./header-bar";
import { SidebarNav } from "./sidebar-nav";
import { primaryNavItems, secondaryNavItems } from "../shared/config/nav-items";
import type { PageMeta } from "../shared/types/page-meta";
import { cn } from "../shared/lib/cn";

const defaultMeta: PageMeta = {
  title: "Push Center",
  description: "Templates and schedules",
};

export function AppShell() {
  const { pathname } = useLocation();
  const { theme, setTheme } = useThemePreference();
  const sidebarCollapsed = useBooleanWorkbenchPreference(SIDEBAR_COLLAPSED_STORAGE_KEY, false);
  const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false);
  const navItems = [...primaryNavItems, ...secondaryNavItems];
  const meta = navItems.find((item) => item.to === pathname) ?? defaultMeta;

  return (
    <div className="flex h-screen overflow-hidden bg-canvas text-ink">
      <aside
        className={cn(
          "hidden min-h-0 shrink-0 border-r border-line bg-surface transition-[width,padding] duration-180 lg:block",
          sidebarCollapsed.value ? "w-[72px] p-3" : "w-56 p-4",
        )}
      >
        <SidebarNav
          collapsed={sidebarCollapsed.value}
          onToggleCollapsed={() => sidebarCollapsed.setValue(!sidebarCollapsed.value)}
        />
      </aside>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <HeaderBar
          meta={meta}
          onOpenNavigation={() => setMobileNavigationOpen(true)}
          onThemeChange={setTheme}
          theme={theme}
        />
        <main className="min-h-0 flex-1 overflow-y-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>

      <div
        aria-hidden={!mobileNavigationOpen}
        className={cn(
          "fixed inset-0 z-50 lg:hidden",
          mobileNavigationOpen ? "pointer-events-auto" : "pointer-events-none",
        )}
        data-open={mobileNavigationOpen ? "true" : "false"}
        data-testid="mobile-navigation"
      >
        <button
          aria-label="关闭导航遮罩"
          className={cn(
            "absolute inset-0 bg-slate-950/40 transition-opacity duration-180",
            mobileNavigationOpen ? "opacity-100" : "opacity-0",
          )}
          onClick={() => setMobileNavigationOpen(false)}
          tabIndex={mobileNavigationOpen ? 0 : -1}
          type="button"
        />
        <aside
          className={cn(
            "absolute inset-y-0 left-0 w-[min(88vw,280px)] border-r border-line bg-surface p-4 shadow-xl transition-transform duration-180",
            mobileNavigationOpen ? "translate-x-0" : "-translate-x-full",
          )}
        >
          <button
            aria-label="关闭导航"
            className="workbench-icon-button absolute right-3 top-3 z-10"
            onClick={() => setMobileNavigationOpen(false)}
            tabIndex={mobileNavigationOpen ? 0 : -1}
            type="button"
          >
            <XMarkIcon aria-hidden="true" className="h-5 w-5" />
          </button>
          {mobileNavigationOpen ? (
            <SidebarNav
              collapsed={false}
              onToggleCollapsed={() => setMobileNavigationOpen(false)}
            />
          ) : null}
        </aside>
      </div>
    </div>
  );
}
