import { Navigate, type RouteObject } from "react-router-dom";
import { AppShell } from "../layouts/app-shell";
import { DashboardPage } from "../pages/dashboard-page";
import { NewsPage } from "../pages/news-page";
import { ModulePlaceholderPage } from "../pages/module-placeholder-page";

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
        element: <ModulePlaceholderPage />,
        handle: { title: "Macro", description: "Indicators and comparisons" },
      },
      {
        path: "market",
        element: <ModulePlaceholderPage />,
        handle: { title: "Market", description: "Signals and watchlists" },
      },
      {
        path: "events",
        element: <ModulePlaceholderPage />,
        handle: { title: "Events", description: "Timeline and watch windows" },
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
