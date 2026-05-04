import { useQuery } from "@tanstack/react-query";
import { getMarketDataModule } from "../api/get-market-data-module";
import type { MarketDataTab } from "../model/market-data.types";

export function useMarketDataModuleQuery(activeTab: MarketDataTab) {
  return useQuery({
    queryKey: ["market-data-module", activeTab],
    queryFn: ({ signal }) => getMarketDataModule({ tab: activeTab, signal }),
  });
}
