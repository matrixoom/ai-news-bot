import { useQuery } from "@tanstack/react-query";
import { getNewsModule } from "../api/get-news-module";
import { adaptNewsModule } from "../model/news-module-adapter";
import { useNewsMode } from "../../../shared/hooks/use-news-mode";

export function useNewsModuleQuery() {
  const { newsMode } = useNewsMode();

  return useQuery({
    queryKey: ["news-module", newsMode],
    staleTime: 60_000,
    queryFn: ({ signal }) => getNewsModule(signal, newsMode).then(adaptNewsModule),
  });
}
