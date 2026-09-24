import {
  Checkbox,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  TextArea,
  TextField,
} from "@/components/ui";
import type { CustomFieldDefinition, CustomFieldValues } from "../types";

const NONE = "__none__";

/**
 * The tenant's own fields, rendered into whatever form is open. One control per
 * definition and nothing clever: the validation that matters runs on the server,
 * where a value that skipped the form still has to pass.
 */
export function CustomFieldInputs({
  fields,
  values,
  onChange,
  disabled = false,
}: {
  fields: CustomFieldDefinition[];
  values: CustomFieldValues;
  onChange: (values: CustomFieldValues) => void;
  disabled?: boolean;
}) {
  if (fields.length === 0) return null;
  const set = (key: string, value: string | number | boolean | null) => {
    const next = { ...values };
    if (value === null || value === "") delete next[key];
    else next[key] = value;
    onChange(next);
  };

  return (
    <div className="space-y-3.5">
      {fields.map((f) => {
        const raw = values[f.key];
        const text = raw === undefined || raw === null ? "" : String(raw);
        if (f.field_type === "checkbox") {
          return (
            <label key={f.id} className="flex items-start gap-2.5">
              <Checkbox
                id={`cf-${f.id}`}
                checked={raw === true}
                onCheckedChange={(v) => set(f.key, v === true)}
                disabled={disabled}
              />
              <span>
                <span className="block text-body-md text-text-primary">{f.label}</span>
                {f.help_text ? (
                  <span className="block text-caption text-text-subtle">{f.help_text}</span>
                ) : null}
              </span>
            </label>
          );
        }
        if (f.field_type === "select") {
          return (
            <div key={f.id}>
              <SelectField label={f.label} optional={!f.required}>
                <Select
                  value={text || NONE}
                  onValueChange={(v) => set(f.key, v === NONE ? null : v)}
                  disabled={disabled}
                >
                  <SelectTrigger aria-label={f.label} />
                  <SelectContent>
                    <SelectItem value={NONE}>Not set</SelectItem>
                    {f.options.map((o) => (
                      <SelectItem key={o} value={o}>
                        {o}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </SelectField>
              {f.help_text ? (
                <p className="mt-1.5 text-body-sm text-text-subtle">{f.help_text}</p>
              ) : null}
            </div>
          );
        }
        if (f.field_type === "textarea") {
          return (
            <TextArea
              key={f.id}
              label={f.label}
              optional={!f.required}
              hint={f.help_text ?? undefined}
              rows={3}
              value={text}
              disabled={disabled}
              onChange={(e) => set(f.key, e.target.value)}
            />
          );
        }
        return (
          <TextField
            key={f.id}
            label={f.label}
            optional={!f.required}
            hint={f.help_text ?? undefined}
            type={f.field_type === "number" ? "number" : f.field_type === "date" ? "date" : "text"}
            value={text}
            disabled={disabled}
            onChange={(e) =>
              set(
                f.key,
                f.field_type === "number" && e.target.value !== ""
                  ? Number(e.target.value)
                  : e.target.value,
              )
            }
          />
        );
      })}
    </div>
  );
}
