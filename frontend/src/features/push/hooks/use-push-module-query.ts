import { useQuery } from "@tanstack/react-query";
import { getPushModule } from "../api/get-push-module";
import { adaptPushModule } from "../model/push-module-adapter";
import type { PushModuleTab } from "../model/push-module.types";

export function usePushModuleQuery(activeTab: PushModuleTab) {
  const includePreview = activeTab !== "history";
  return useQuery({
    queryKey: ["push-module", includePreview],
    staleTime: 15_000,
    queryFn: ({ signal }) => getPushModule({ signal, includePreview }).then(adaptPushModule),
    refetchInterval: (query) => (query.state.data?.moduleLoading ? query.state.data.refreshAfterMs : false),
  });
}
