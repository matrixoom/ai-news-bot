import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createEventOutlookEvent, type CreateEventOutlookEventInput } from "../api/create-event-outlook-event";
import { updateEventOutlookEvent, type UpdateEventOutlookEventInput } from "../api/update-event-outlook-event";

export function useCreateEventOutlookEventMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateEventOutlookEventInput) => createEventOutlookEvent(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["event-outlook-module"] });
    },
  });
}

export function useUpdateEventOutlookEventMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateEventOutlookEventInput) => updateEventOutlookEvent(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["event-outlook-module"] });
    },
  });
}
