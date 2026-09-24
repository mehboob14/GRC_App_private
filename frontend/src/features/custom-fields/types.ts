/** Fields a workspace adds to a kind of record, and the values written against them. */

export const CUSTOM_FIELD_TYPES = [
  "text",
  "textarea",
  "number",
  "date",
  "select",
  "checkbox",
] as const;
export type CustomFieldType = (typeof CUSTOM_FIELD_TYPES)[number];

/** The modules that carry custom fields. The path is the module's own prefix,
 *  so each one's settings routes are guarded by that module's permission. */
export type CustomFieldScope = "assets" | "vulnerabilities";

export type CustomFieldDefinition = {
  id: string;
  /** Stable key in the record's `custom_fields` map. Never renamed. */
  key: string;
  label: string;
  field_type: CustomFieldType;
  options: string[];
  help_text: string | null;
  required: boolean;
  position: number;
  archived: boolean;
};

export type CustomFieldInput = {
  label: string;
  field_type: CustomFieldType;
  options: string[];
  help_text: string | null;
  required: boolean;
  position: number;
};

/** What a record stores: key to a string, number or boolean. */
export type CustomFieldValues = Record<string, string | number | boolean>;

export const FIELD_TYPE_LABEL: Record<CustomFieldType, string> = {
  text: "Text",
  textarea: "Long text",
  number: "Number",
  date: "Date",
  select: "Choice",
  checkbox: "Yes or no",
};

export const FIELD_TYPE_HINT: Record<CustomFieldType, string> = {
  text: "One line, up to 2000 characters.",
  textarea: "Several lines.",
  number: "A whole number or a decimal.",
  date: "A single date.",
  select: "One of a list you set.",
  checkbox: "A tick box.",
};
