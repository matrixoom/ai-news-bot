import { Outlet, useLocation } from "react-router-dom";
import { useMarketTicker } from "../shared/hooks/use-market-ticker";
import { useNewsMode } from "../shared/hooks/use-news-mode";
import { useThemePreference } from "../shared/hooks/use-theme-preference";
import { useBooleanWorkbenchPreference } from "../shared/hooks/use-workbench-preference";
import {
  SHOW_MARKET_TICKER_STORAGE_KEY,
  SIDEBAR_COLLAPSED_STORAGE_KEY,
} from "../shared/lib/workbench-preferences";
import { HeaderBar } from "./header-bar";
import { SidebarNav } from "./sidebar-nav";
import { primaryNavItems, secondaryNavItems } from "../shared/config/nav-items";
import type { PageMeta } from "../shared/types/page-meta";
import { cn } from "../shared/lib/cn";

const defaultMeta: PageMeta = {
  title: "Dashboard",
  description: "Cross-module overview",
};

export function AppShell() {
  const { pathname } = useLocation();
  useNewsMode();
  const { theme, setTheme } = useThemePreference();
  const showMarketTicker = useBooleanWorkbenchPreference(SHOW_MARKET_TICKER_STORAGE_KEY, true);
  const sidebarCollapsed = useBooleanWorkbenchPreference(SIDEBAR_COLLAPSED_STORAGE_KEY, false);
  const marketTickerQuery = useMarketTicker();
  const navItems = [...primaryNavItems, ...secondaryNavItems];
  const meta = navItems.find((item) => item.to === pathname) ?? defaultMeta;

  return (
    <div
      className={cn(
        "grid h-screen overflow-hidden bg-slate-100 transition-[grid-template-columns] duration-200",
        sidebarCollapsed.value ? "grid-cols-[88px_1fr]" : "grid-cols-[280px_1fr]",
      )}
    >
      <aside
        className={cn(
          "min-h-0 border-r border-slate-200 bg-white transition-all duration-200",
          sidebarCollapsed.value ? "p-3" : "p-6",
        )}
      >
        <SidebarNav
          collapsed={sidebarCollapsed.value}
          onToggleCollapsed={() => sidebarCollapsed.setValue(!sidebarCollapsed.value)}
        />
      </aside>
      <div className="flex min-h-0 flex-col">
        <HeaderBar
          marketTickerItems={marketTickerQuery.data ?? []}
          marketTickerLoading={marketTickerQuery.isPending}
          meta={meta}
          onThemeChange={setTheme}
          showMarketTicker={showMarketTicker.value}
          theme={theme}
        />
        <main className="flex-1 min-h-0 overflow-y-auto p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
