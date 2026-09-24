import type { CustomFieldDefinition } from "./types";

/** The same values, read only: what a detail page shows under "More". */
export function customFieldText(
  field: CustomFieldDefinition,
  value: string | number | boolean | undefined,
): string {
  if (value === undefined || value === null || value === "") return "Not set";
  if (field.field_type === "checkbox") return value ? "Yes" : "No";
  return String(value);
}
