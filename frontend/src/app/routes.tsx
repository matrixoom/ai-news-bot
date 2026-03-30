import { Navigate, type RouteObject } from "react-router-dom";
import { AppShell } from "../layouts/app-shell";
import { DashboardPage } from "../pages/dashboard-page";
import { EventsPage } from "../pages/events-page";
import { MacroPage } from "../pages/macro-page";
import { MarketPage } from "../pages/market-page";
import { NewsPage } from "../pages/news-page";
import { ModulePlaceholderPage } from "../pages/module-placeholder-page";
import { StatusPage } from "../pages/status-page";

export const appRoutes: RouteObject[] = [
  {
    path: "/",
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />,
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
        element: <ModulePlaceholderPage />,
        handle: { title: "Push Center", description: "Templates and schedules" },
      },
      {
        path: "settings",
        element: <ModulePlaceholderPage />,
        handle: { title: "Settings", description: "Preferences and system defaults" },
      },
    ],
  },
];
