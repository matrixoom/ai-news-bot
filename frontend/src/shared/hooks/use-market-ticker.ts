import { useQuery } from "@tanstack/react-query";
import { adaptMarketModule } from "../../features/market/model/market-module-adapter";
import { getMarketModule } from "../../features/market/api/get-market-module";

export function useMarketTicker() {
  return useQuery({
    queryKey: ["market-module"],
    staleTime: 60_000,
    queryFn: ({ signal }) => getMarketModule(signal).then(adaptMarketModule),
    select: (model) => model.signalCards.slice(0, 4),
  });
}
