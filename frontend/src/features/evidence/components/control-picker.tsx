import { useEffect, useMemo, useRef, useState } from "react";
import { Checkbox, Icon } from "@/components/ui";
import { cn } from "@/lib/cn";
import type { Control } from "@/lib/api/types";

export type ControlGroup = {
  /** Criterion code, e.g. "CC6.1". */
  criterion: string;
  /** Criterion code + name for the group header. */
  label: string;
  controls: Control[];
};

/**
 * Searchable, criteria-grouped control picker — a combobox that expands inline
 * (a floating layer would be clipped by the dialog's scroll container). Multi
 * select; the criterion is the hierarchy, controls sit under it.
 */
export function ControlPicker({
  groups,
  value,
  onChange,
  loading = false,
}: {
  groups: ControlGroup[];
  value: string[];
  onChange: (ids: string[]) => void;
  loading?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDown(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  const byId = useMemo(() => {
    const map = new Map<string, Control>();
    for (const group of groups) for (const control of group.controls) map.set(control.id, control);
    return map;
  }, [groups]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return groups;
    return groups
      .map((group) => ({
        ...group,
        controls: group.controls.filter(
          (control) =>
            control.name.toLowerCase().includes(q) ||
            control.code.toLowerCase().includes(q) ||
            control.category.toLowerCase().includes(q) ||
            group.label.toLowerCase().includes(q),
        ),
      }))
      .filter((group) => group.controls.length > 0);
  }, [groups, query]);

  function toggle(id: string, on: boolean) {
    onChange(on ? [...new Set([...value, id])] : value.filter((existing) => existing !== id));
  }

  const selected = value.map((id) => byId.get(id)).filter((c): c is Control => Boolean(c));

  return (
    <div
      ref={ref}
      className="relative"
      onKeyDown={(event) => {
        if (event.key === "Escape" && open) {
          event.stopPropagation();
          setOpen(false);
        }
      }}
    >
      {/* Search field — the combobox trigger */}
      <div
        className={cn(
          "flex items-center gap-2 rounded-full border bg-surface-primary px-3.5 py-2 transition-colors",
          open ? "border-action-accent shadow-input-focus" : "border-border",
        )}
      >
        <Icon name="search" className="size-4 shrink-0 text-text-subtle" />
        <input
          type="text"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onFocus={() => setOpen(true)}
          placeholder="Search controls by name, code or criterion…"
          className="w-full bg-transparent text-body-sm text-text-primary outline-none placeholder:text-text-subtle"
        />
        {value.length > 0 ? (
          <button
            type="button"
            onClick={() => onChange([])}
            className="shrink-0 text-caption font-medium text-text-subtle hover:text-text-primary"
          >
            Clear
          </button>
        ) : null}
      </div>

      {/* Selected chips */}
      {selected.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {selected.map((control) => (
            <span
              key={control.id}
              className="inline-flex items-center gap-1 rounded-full bg-action-accent-tint py-0.5 pl-2.5 pr-1 text-caption font-medium text-action-accent"
            >
              <span className="max-w-[180px] truncate">{control.name}</span>
              <button
                type="button"
                onClick={() => toggle(control.id, false)}
                aria-label={`Remove ${control.name}`}
                className="flex size-4 items-center justify-center rounded-full hover:bg-action-accent/20"
              >
                <Icon name="x" className="size-3" />
              </button>
            </span>
          ))}
        </div>
      ) : null}

      {/* Dropdown panel */}
      {open ? (
        <div className="mt-2 max-h-64 overflow-y-auto rounded-lg border border-border bg-surface-primary shadow-3">
          {loading ? (
            <p className="px-3 py-6 text-center text-caption text-text-subtle">Loading controls…</p>
          ) : filtered.length === 0 ? (
            <p className="px-3 py-6 text-center text-caption text-text-subtle">
              No controls match “{query}”.
            </p>
          ) : (
            filtered.map((group) => (
              <div key={group.criterion}>
                <p className="sticky top-0 z-10 border-b border-border bg-surface-sunken px-3 py-1.5 type-overline">
                  {group.label}
                </p>
                {group.controls.map((control) => {
                  const checked = value.includes(control.id);
                  return (
                    <label
                      key={`${group.criterion}-${control.id}`}
                      className="flex cursor-pointer items-center gap-3 px-3 py-2 hover:bg-surface-hover"
                    >
                      <Checkbox
                        checked={checked}
                        onCheckedChange={(next) => toggle(control.id, next)}
                        aria-label={control.name}
                      />
                      <span
                        className={cn(
                          "flex size-8 shrink-0 items-center justify-center rounded-full",
                          checked
                            ? "bg-action-accent text-action-primary-fg"
                            : "bg-action-accent-tint text-action-accent",
                        )}
                      >
                        <Icon name="controls" className="size-4" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-body-sm font-medium text-text-primary">
                          {control.name}
                        </span>
                        <span className="block truncate text-caption text-text-subtle">
                          {control.category}
                        </span>
                      </span>
                    </label>
                  );
                })}
              </div>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}
