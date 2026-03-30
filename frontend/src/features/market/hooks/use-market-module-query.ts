import { useQuery } from "@tanstack/react-query";
import { getMarketModule } from "../api/get-market-module";
import { adaptMarketModule } from "../model/market-module-adapter";

export function useMarketModuleQuery() {
  return useQuery({
    queryKey: ["market-module"],
    staleTime: 60_000,
    queryFn: ({ signal }) => getMarketModule(signal).then(adaptMarketModule),
  });
}
