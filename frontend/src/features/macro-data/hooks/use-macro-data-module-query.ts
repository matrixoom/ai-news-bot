import { useQuery } from "@tanstack/react-query";
import { getMacroDataModule } from "../api/get-macro-data-module";
import type { MacroDataTab } from "../model/macro-data.types";

export function useMacroDataModuleQuery(activeTab: MacroDataTab) {
  return useQuery({
    queryKey: ["macro-data-module", activeTab],
    queryFn: ({ signal }) => getMacroDataModule({ tab: activeTab, signal }),
  });
}
