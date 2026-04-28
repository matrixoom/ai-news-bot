import { useQuery } from "@tanstack/react-query";
import { getMacroModule } from "../api/get-macro-module";
import { adaptMacroModule } from "../model/macro-module-adapter";

export function useMacroModuleQuery() {
  return useQuery({
    queryKey: ["macro-module"],
    staleTime: 60_000,
    queryFn: ({ signal }) => getMacroModule(signal).then(adaptMacroModule),
  });
}
