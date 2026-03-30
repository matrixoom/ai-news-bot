import type { DashboardResponse, DashboardViewModel } from "./dashboard.types";

export function adaptDashboard(response: DashboardResponse): DashboardViewModel {
  return {
    hero: response.hero,
    stats: response.stats,
    brief: response.brief,
    moduleSectionTitle: "Module snapshots",
    modules: response.modules,
  };
}
