import { useQuery } from "@tanstack/react-query";
import { getPushModule } from "../api/get-push-module";
import { adaptPushModule } from "../model/push-module-adapter";

export function usePushModuleQuery() {
  return useQuery({
    queryKey: ["push-module"],
    staleTime: 15_000,
    queryFn: ({ signal }) => getPushModule(signal).then(adaptPushModule),
    refetchInterval: (query) => (query.state.data?.moduleLoading ? query.state.data.refreshAfterMs : false),
  });
}
