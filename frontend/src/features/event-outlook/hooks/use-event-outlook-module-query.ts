import { useQuery } from "@tanstack/react-query";
import { getEventOutlookModule } from "../api/get-event-outlook-module";
import type { EventOutlookRegion } from "../model/event-outlook.types";

export function useEventOutlookModuleQuery({
  region,
  startDate,
  endDate,
  refreshToken,
}: {
  region: EventOutlookRegion;
  startDate: string;
  endDate: string;
  refreshToken: number;
}) {
  return useQuery({
    queryKey: ["event-outlook-module", region, startDate, endDate, refreshToken],
    queryFn: ({ signal }) =>
      getEventOutlookModule({
        region,
        startDate,
        endDate,
        refresh: refreshToken > 0,
        signal,
      }),
  });
}
