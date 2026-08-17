import * as DropdownMenuPrimitive from "@radix-ui/react-dropdown-menu";
import { useMemo, useState } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";

export type FilterFacetOption = {
  value: string;
  label: string;
};

type FilterFacetProps = {
  /** The facet name shown on the chip, e.g. "Status". */
  label: string;
  options: FilterFacetOption[];
  /** Currently selected option values (multi-select). */
  values: string[];
  onChange: (values: string[]) => void;
  /** Show a search box once the list is long enough to need one. */
  searchable?: boolean;
  className?: string;
};

/** The chip always states its current selection, never just its own name. */
function summarise(options: FilterFacetOption[], values: string[]): string {
  if (values.length === 0) return "All";
  if (values.length === 1) {
    return options.find((option) => option.value === values[0])?.label ?? values[0];
  }
  return `${values.length} selected`;
}

/**
 * Toolbar filter facet — a rounded `Label: Value` pill that reads as a
 * sentence, so the active filter state is legible without opening anything.
 * Resting is neutral; with a selection it takes the accent tint and border.
 */
export function FilterFacet({
  label,
  options,
  values,
  onChange,
  searchable,
  className,
}: FilterFacetProps) {
  const [query, setQuery] = useState("");
  const active = values.length > 0;
  // Long lists get a search box automatically; short ones never need one.
  const withSearch = searchable ?? options.length > 8;

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter((option) => option.label.toLowerCase().includes(q));
  }, [options, query]);

  const toggle = (value: string, checked: boolean) => {
    onChange(checked ? [...values, value] : values.filter((v) => v !== value));
  };

  return (
    <DropdownMenuPrimitive.Root
      onOpenChange={(open) => {
        if (!open) setQuery("");
      }}
    >
      <DropdownMenuPrimitive.Trigger
        className={cn(
          "inline-flex h-9 max-w-[240px] items-center gap-1.5 rounded-full border px-3.5",
          "font-sans text-label-sm transition-colors duration-80 ease-state",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
          active
            ? "border-action-accent-border bg-action-accent-tint text-action-accent"
            : "border-border bg-surface-primary text-text-secondary hover:bg-surface-hover",
          className,
        )}
      >
        <span className="shrink-0 font-semibold">{label}:</span>
        <span className={cn("truncate", active ? "font-bold" : "text-text-primary")}>
          {summarise(options, values)}
        </span>
        <Icon name="chev" className="size-3.5 shrink-0 opacity-70" />
      </DropdownMenuPrimitive.Trigger>

      <DropdownMenuPrimitive.Portal>
        <DropdownMenuPrimitive.Content
          sideOffset={6}
          align="start"
          className="z-[1360] min-w-[220px] max-w-[300px] overflow-hidden rounded-lg border border-border bg-surface-primary p-1 shadow-2"
        >
          {withSearch ? (
            <div className="mb-1 flex items-center gap-2 border-b border-border px-2.5 py-2">
              <Icon name="search" className="size-3.5 shrink-0 text-text-subtle" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={`Search ${label.toLowerCase()}…`}
                aria-label={`Search ${label}`}
                // Everything but menu navigation belongs to the input, or the
                // menu's own typeahead swallows what is typed.
                onKeyDown={(event) => {
                  if (!["ArrowDown", "ArrowUp", "Escape", "Tab"].includes(event.key)) {
                    event.stopPropagation();
                  }
                }}
                className="w-full bg-transparent text-body-sm text-text-primary outline-none placeholder:text-text-subtle"
              />
            </div>
          ) : null}

          <div className="max-h-64 overflow-y-auto">
            {filtered.length === 0 ? (
              <p className="px-2.5 py-4 text-center text-caption text-text-subtle">
                No matches.
              </p>
            ) : (
              filtered.map((option) => (
                <DropdownMenuPrimitive.CheckboxItem
                  key={option.value}
                  checked={values.includes(option.value)}
                  onCheckedChange={(checked) => toggle(option.value, checked === true)}
                  onSelect={(event) => event.preventDefault()}
                  className={cn(
                    "relative flex min-h-8 cursor-pointer select-none items-center gap-2 rounded-xs py-1.5 pl-7 pr-2.5 text-body-md outline-none",
                    "text-text-primary data-[highlighted]:bg-surface-hover",
                    "data-[disabled]:pointer-events-none data-[disabled]:text-text-faint",
                  )}
                >
                  <DropdownMenuPrimitive.ItemIndicator className="absolute left-2 text-action-accent">
                    <Icon name="check" className="size-3.5" strokeWidth={2.5} />
                  </DropdownMenuPrimitive.ItemIndicator>
                  {option.label}
                </DropdownMenuPrimitive.CheckboxItem>
              ))
            )}
          </div>

          <DropdownMenuPrimitive.Separator className="my-1 h-px bg-border" />
          <DropdownMenuPrimitive.Item
            disabled={!active}
            onSelect={() => onChange([])}
            className={cn(
              "flex h-8 cursor-pointer select-none items-center rounded-xs px-2.5 text-label-sm outline-none",
              "text-text-secondary data-[highlighted]:bg-surface-hover data-[highlighted]:text-text-primary",
              "data-[disabled]:pointer-events-none data-[disabled]:text-text-faint",
            )}
          >
            Clear filter
          </DropdownMenuPrimitive.Item>
        </DropdownMenuPrimitive.Content>
      </DropdownMenuPrimitive.Portal>
    </DropdownMenuPrimitive.Root>
  );
}
