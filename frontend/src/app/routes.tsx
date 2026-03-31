import { Navigate, type RouteObject } from "react-router-dom";
import { AppShell } from "../layouts/app-shell";
import { DashboardPage } from "../pages/dashboard-page";
import { EventsPage } from "../pages/events-page";
import { MacroPage } from "../pages/macro-page";
import { MarketPage } from "../pages/market-page";
import { NewsPage } from "../pages/news-page";
import { PushPage } from "../pages/push-page";
import { SettingsPage } from "../pages/settings-page";
import { StatusPage } from "../pages/status-page";
import { DEFAULT_ROUTE_STORAGE_KEY, readStringPreference } from "../shared/lib/workbench-preferences";

function AppIndexRedirect() {
  const defaultRoute = readStringPreference(DEFAULT_ROUTE_STORAGE_KEY, "/dashboard");
  const allowedRoutes = new Set(["/dashboard", "/news", "/macro", "/market", "/events", "/push", "/status", "/settings"]);
  const nextRoute = allowedRoutes.has(defaultRoute) ? defaultRoute : "/dashboard";

  return <Navigate to={nextRoute} replace />;
}

export const appRoutes: RouteObject[] = [
  {
    path: "/",
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <AppIndexRedirect />,
      },
      {
        path: "dashboard",
        element: <DashboardPage />,
        handle: { title: "Dashboard", description: "Cross-module overview" },
      },
      {
        path: "news",
        element: <NewsPage />,
        handle: { title: "News", description: "Intelligence workbench" },
      },
      {
        path: "macro",
        element: <MacroPage />,
        handle: { title: "Macro", description: "Indicators and comparisons" },
      },
      {
        path: "market",
        element: <MarketPage />,
        handle: { title: "Market", description: "Signals and watchlists" },
      },
      {
        path: "events",
        element: <EventsPage />,
        handle: { title: "Events", description: "Timeline and watch windows" },
      },
      {
        path: "status",
        element: <StatusPage />,
        handle: { title: "Status", description: "Freshness and source health" },
      },
      {
        path: "push",
        element: <PushPage />,
        handle: { title: "Push Center", description: "Templates and schedules" },
      },
      {
        path: "settings",
        element: <SettingsPage />,
        handle: { title: "Settings", description: "Preferences and system defaults" },
      },
    ],
  },
];
