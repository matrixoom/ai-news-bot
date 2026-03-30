import { useEffect, useState } from "react";
import { getDashboard } from "../api/get-dashboard";
import { adaptDashboard } from "../model/dashboard-adapter";
import type { DashboardViewModel } from "../model/dashboard.types";

type DashboardQueryState = {
  data: DashboardViewModel | null;
  error: Error | null;
  isLoading: boolean;
  retry: () => void;
};

export function useDashboardQuery(): DashboardQueryState {
  const [data, setData] = useState<DashboardViewModel | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [requestId, setRequestId] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let isActive = true;

    async function loadDashboard() {
      setIsLoading(true);
      setError(null);

      try {
        const response = await getDashboard(controller.signal);

        if (!isActive) {
          return;
        }

        setData(adaptDashboard(response));
      } catch (caughtError) {
        if (!isActive || controller.signal.aborted) {
          return;
        }

        setError(caughtError instanceof Error ? caughtError : new Error("Failed to load dashboard"));
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void loadDashboard();

    return () => {
      isActive = false;
      controller.abort();
    };
  }, [requestId]);

  return {
    data,
    error,
    isLoading,
    retry: () => {
      setRequestId((value) => value + 1);
    },
  };
}
