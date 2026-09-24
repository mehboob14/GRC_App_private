import { useQuery } from "@tanstack/react-query";
import { listCustomFields } from "./api";
import type { CustomFieldScope } from "./types";

export function customFieldsKey(scope: CustomFieldScope, includeArchived = false) {
  return ["custom-fields", scope, includeArchived] as const;
}

/** The fields a form should render: active ones, in the order the settings set. */
export function useCustomFields(scope: CustomFieldScope, includeArchived = false) {
  return useQuery({
    queryKey: customFieldsKey(scope, includeArchived),
    queryFn: () => listCustomFields(scope, includeArchived),
    staleTime: 60_000,
  });
}
