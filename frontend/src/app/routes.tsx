import { Navigate, type RouteObject } from "react-router-dom";
import { AppShell } from "../layouts/app-shell";
import { PushPage } from "../pages/push-page";
import { SettingsPage } from "../pages/settings-page";
import { StatusPage } from "../pages/status-page";
import { DEFAULT_ROUTE_STORAGE_KEY, readStringPreference } from "../shared/lib/workbench-preferences";

function AppIndexRedirect() {
  const defaultRoute = readStringPreference(DEFAULT_ROUTE_STORAGE_KEY, "/push");
  const allowedRoutes = new Set(["/push", "/status", "/settings"]);
  const nextRoute = allowedRoutes.has(defaultRoute) ? defaultRoute : "/push";

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
