import { Navigate, type RouteObject } from "react-router-dom";
import { AppShell } from "../layouts/app-shell";
import { MacroPage } from "../pages/macro-page";
import { PushPage } from "../pages/push-page";
import { SettingsPage } from "../pages/settings-page";
import { DEFAULT_ROUTE_STORAGE_KEY, readStringPreference } from "../shared/lib/workbench-preferences";

function AppIndexRedirect() {
  const defaultRoute = readStringPreference(DEFAULT_ROUTE_STORAGE_KEY, "/push");
  const allowedRoutes = new Set(["/macro-data", "/push", "/settings"]);
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
        path: "macro-data",
        element: <MacroPage />,
        handle: { title: "Macro Data", description: "GDP, credit, and inflation indicators" },
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
