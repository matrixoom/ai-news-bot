import { useQuery } from "@tanstack/react-query";
import { getDashboard } from "../api/get-dashboard";
import { adaptDashboard } from "../model/dashboard-adapter";

export function useDashboardQuery() {
  return useQuery({
    queryKey: ["dashboard"],
    staleTime: 60_000,
    queryFn: ({ signal }) => getDashboard(signal).then(adaptDashboard),
  });
}
