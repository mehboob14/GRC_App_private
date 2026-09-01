import { Avatar } from "@/components/ui/avatar";
import { Icon } from "@/components/ui/icon";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { cn } from "@/lib/cn";

/**
 * The standard people pickers for the whole app — a searchable dropdown of
 * users with an avatar and email on each row, built on `SearchableSelect`.
 * `PersonSelect` picks one; `PeopleSelect` picks several (the chosen set shows
 * as removable chips). Every module's owner / assignee / reviewer field should
 * use these, so person selection looks and behaves the same everywhere.
 */

export type Person = { id: string; name: string; email?: string };

function optionsOf(people: Person[]) {
  return people.map((p) => ({ value: p.id, label: p.name, sublabel: p.email }));
}

function Row({ name, email }: { name: string; email?: string }) {
  return (
    <span className="flex min-w-0 items-center gap-2.5">
      <Avatar name={name} size="sm" seed={email} />
      <span className="min-w-0">
        <span className="block truncate text-body-md text-text-primary">{name}</span>
        {email ? <span className="block truncate text-caption text-text-subtle">{email}</span> : null}
      </span>
    </span>
  );
}

export function PersonSelect({
  people,
  value,
  onChange,
  placeholder = "Select a person…",
  clearLabel,
  disabled,
  "aria-label": ariaLabel,
}: {
  people: Person[];
  value: string | null;
  onChange: (value: string | null) => void;
  placeholder?: string;
  clearLabel?: string;
  disabled?: boolean;
  "aria-label"?: string;
}) {
  const selected = people.find((p) => p.id === value) ?? null;
  return (
    <SearchableSelect
      options={optionsOf(people)}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      searchPlaceholder="Search users…"
      clearLabel={clearLabel}
      disabled={disabled}
      aria-label={ariaLabel}
      renderOption={(o) => <Row name={o.label} email={o.sublabel} />}
      renderValue={(o) =>
        o && selected ? (
          <span className="flex min-w-0 items-center gap-2">
            <Avatar name={selected.name} size="sm" seed={selected.email} />
            <span className="truncate text-text-primary">{selected.name}</span>
          </span>
        ) : (
          <span className="text-text-faint">{placeholder}</span>
        )
      }
    />
  );
}

export function PeopleSelect({
  people,
  values,
  onChange,
  placeholder = "Add people…",
}: {
  people: Person[];
  values: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
}) {
  const chosen = values.map((id) => people.find((p) => p.id === id)).filter((p): p is Person => Boolean(p));
  const available = people.filter((p) => !values.includes(p.id));
  return (
    <div className="space-y-2">
      <PersonSelect
        people={available}
        value={null}
        onChange={(id) => id && onChange([...values, id])}
        placeholder={placeholder}
        aria-label={placeholder}
      />
      {chosen.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {chosen.map((p) => (
            <span
              key={p.id}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-primary py-0.5 pl-0.5 pr-2 text-body-sm text-text-primary",
              )}
            >
              <Avatar name={p.name} size="sm" seed={p.email} />
              {p.name}
              <button
                type="button"
                aria-label={`Remove ${p.name}`}
                onClick={() => onChange(values.filter((v) => v !== p.id))}
                className="text-text-subtle transition-colors hover:text-text-primary"
              >
                <Icon name="x" className="size-3.5" />
              </button>
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}
