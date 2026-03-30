import { useQuery } from "@tanstack/react-query";
import { getEventsModule } from "../api/get-events-module";
import { adaptEventsModule } from "../model/events-module-adapter";

export function useEventsModuleQuery() {
  return useQuery({
    queryKey: ["events-module"],
    staleTime: 60_000,
    queryFn: ({ signal }) => getEventsModule(signal).then(adaptEventsModule),
  });
}
