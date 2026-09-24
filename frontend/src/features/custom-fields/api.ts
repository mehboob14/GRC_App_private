import { apiFetch } from "@/lib/api/client";
import type { CustomFieldDefinition, CustomFieldInput, CustomFieldScope } from "./types";

/** Each module owns its own definitions endpoint, so the route carries that
 *  module's read/manage permission rather than a shared one nobody has. */
export async function listCustomFields(
  scope: CustomFieldScope,
  includeArchived = false,
): Promise<CustomFieldDefinition[]> {
  const query = includeArchived ? "?include_archived=true" : "";
  const out = await apiFetch<{ items: CustomFieldDefinition[] }>(
    `/${scope}/custom-fields${query}`,
  );
  return out.items;
}

export function createCustomField(
  scope: CustomFieldScope,
  body: CustomFieldInput,
): Promise<CustomFieldDefinition> {
  return apiFetch<CustomFieldDefinition>(`/${scope}/custom-fields`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateCustomField(
  scope: CustomFieldScope,
  id: string,
  body: CustomFieldInput,
): Promise<CustomFieldDefinition> {
  return apiFetch<CustomFieldDefinition>(`/${scope}/custom-fields/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function setCustomFieldArchived(
  scope: CustomFieldScope,
  id: string,
  archived: boolean,
): Promise<CustomFieldDefinition> {
  return apiFetch<CustomFieldDefinition>(`/${scope}/custom-fields/${id}/archive`, {
    method: "POST",
    body: JSON.stringify({ archived }),
  });
}
