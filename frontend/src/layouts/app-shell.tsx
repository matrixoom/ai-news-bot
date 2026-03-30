import { Outlet, useLocation } from "react-router-dom";
import { HeaderBar } from "./header-bar";
import { SidebarNav } from "./sidebar-nav";
import { primaryNavItems, secondaryNavItems } from "../shared/config/nav-items";
import type { PageMeta } from "../shared/types/page-meta";

const defaultMeta: PageMeta = {
  title: "Dashboard",
  description: "Cross-module overview",
};

export function AppShell() {
  const { pathname } = useLocation();
  const navItems = [...primaryNavItems, ...secondaryNavItems];
  const meta = navItems.find((item) => item.to === pathname) ?? defaultMeta;

  return (
    <div className="grid min-h-screen grid-cols-[260px_1fr] bg-slate-100">
      <aside className="border-r border-slate-200 bg-white p-6">
        <SidebarNav />
      </aside>
      <div className="flex min-h-screen flex-col">
        <HeaderBar meta={meta} />
        <main className="flex-1 p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
