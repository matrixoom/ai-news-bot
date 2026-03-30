import { useQuery } from "@tanstack/react-query";
import { getNewsModule } from "../api/get-news-module";
import { adaptNewsModule } from "../model/news-module-adapter";

export function useNewsModuleQuery() {
  return useQuery({
    queryKey: ["news-module"],
    staleTime: 60_000,
    queryFn: ({ signal }) => getNewsModule(signal).then(adaptNewsModule),
  });
}
