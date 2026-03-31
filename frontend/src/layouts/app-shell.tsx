import { Outlet, useLocation } from "react-router-dom";
import { useMarketTicker } from "../shared/hooks/use-market-ticker";
import { useNewsMode } from "../shared/hooks/use-news-mode";
import { useThemePreference } from "../shared/hooks/use-theme-preference";
import { useBooleanWorkbenchPreference } from "../shared/hooks/use-workbench-preference";
import { SHOW_MARKET_TICKER_STORAGE_KEY } from "../shared/lib/workbench-preferences";
import { HeaderBar } from "./header-bar";
import { SidebarNav } from "./sidebar-nav";
import { primaryNavItems, secondaryNavItems } from "../shared/config/nav-items";
import type { PageMeta } from "../shared/types/page-meta";
import { useStatusModuleQuery } from "../features/status/hooks/use-status-module-query";

const defaultMeta: PageMeta = {
  title: "Dashboard",
  description: "Cross-module overview",
};

export function AppShell() {
  const { pathname } = useLocation();
  const { newsMode, newsModeOptions, setNewsMode } = useNewsMode();
  const { theme, toggleTheme } = useThemePreference();
  const showMarketTicker = useBooleanWorkbenchPreference(SHOW_MARKET_TICKER_STORAGE_KEY, true);
  const statusQuery = useStatusModuleQuery();
  const marketTickerQuery = useMarketTicker();
  const navItems = [...primaryNavItems, ...secondaryNavItems];
  const meta = navItems.find((item) => item.to === pathname) ?? defaultMeta;

  return (
    <div className="grid min-h-screen grid-cols-[260px_1fr] bg-slate-100">
      <aside className="border-r border-slate-200 bg-white p-6">
        <SidebarNav />
      </aside>
      <div className="flex min-h-screen flex-col">
        <HeaderBar
          freshnessNote={statusQuery.data?.coverageNote ?? "Freshness data loading..."}
          freshnessValue={statusQuery.data?.generatedAt ?? null}
          marketTickerItems={marketTickerQuery.data ?? []}
          marketTickerLoading={marketTickerQuery.isPending}
          meta={meta}
          newsMode={newsMode}
          newsModeOptions={newsModeOptions}
          onNewsModeChange={setNewsMode}
          onThemeToggle={toggleTheme}
          showMarketTicker={showMarketTicker.value}
          theme={theme}
        />
        <main className="flex-1 p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
