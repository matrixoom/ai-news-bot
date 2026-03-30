import { useQuery } from "@tanstack/react-query";
import { getStatusModule } from "../api/get-status-module";
import { adaptStatusModule } from "../model/status-module-adapter";
import { useNewsMode } from "../../../shared/hooks/use-news-mode";

export function useStatusModuleQuery() {
  const { newsMode } = useNewsMode();

  return useQuery({
    queryKey: ["status-module", newsMode],
    staleTime: 60_000,
    queryFn: ({ signal }) => getStatusModule(signal, newsMode).then(adaptStatusModule),
  });
}
