import * as DropdownMenuPrimitive from "@radix-ui/react-dropdown-menu";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";

export type SearchableOption = {
  value: string;
  label: string;
  /** Second line — e.g. an email or a role. Also searched. */
  sublabel?: string;
};

type SearchableSelectProps = {
  options: SearchableOption[];
  value: string | null;
  onChange: (value: string | null) => void;
  /** Shown on the trigger when nothing is selected. */
  placeholder?: string;
  searchPlaceholder?: string;
  /** Offers a row that clears the selection (e.g. "Unassigned"). */
  clearLabel?: string;
  /** Custom trigger body — receives the selected option, or null. */
  renderValue?: (option: SearchableOption | null) => ReactNode;
  /** Custom row body, so callers can add avatars without a second component. */
  renderOption?: (option: SearchableOption) => ReactNode;
  align?: "start" | "end";
  disabled?: boolean;
  className?: string;
  contentClassName?: string;
  "aria-label"?: string;
};

/**
 * A single-select dropdown with a search box — the DS has `Select` (no search)
 * and `FilterFacet` (multi-select, no search); this is the one-of-many-people
 * case, where scanning a list is the wrong interaction.
 *
 * Built on DropdownMenu rather than Select because Radix Select owns its
 * keyboard model and will not host a text input. The input stops keydown
 * propagation so the menu's own typeahead cannot swallow what is typed.
 */
export function SearchableSelect({
  options,
  value,
  onChange,
  placeholder = "Select…",
  searchPlaceholder = "Search…",
  clearLabel,
  renderValue,
  renderOption,
  align = "start",
  disabled,
  className,
  contentClassName,
  "aria-label": ariaLabel,
}: SearchableSelectProps) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // DropdownMenu focuses its content (then the first item) on open and has no
  // `onOpenAutoFocus` to intercept — so take focus back on the next tick.
  useEffect(() => {
    if (!open) return;
    const timer = window.setTimeout(() => inputRef.current?.focus(), 10);
    return () => window.clearTimeout(timer);
  }, [open]);

  const selected = options.find((option) => option.value === value) ?? null;

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter(
      (option) =>
        option.label.toLowerCase().includes(q) ||
        (option.sublabel ?? "").toLowerCase().includes(q),
    );
  }, [options, query]);

  return (
    <DropdownMenuPrimitive.Root
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) setQuery("");
      }}
    >
      <DropdownMenuPrimitive.Trigger
        disabled={disabled}
        // aria-label overrides the trigger's contents, so it has to carry the
        // selected value too or the field announces only its own name.
        aria-label={
          ariaLabel && selected ? `${ariaLabel}: ${selected.label}` : ariaLabel
        }
        className={cn(
          "flex h-9 w-full items-center justify-between gap-2 rounded-sm border border-border bg-surface-primary px-3",
          "text-body-md text-text-primary transition-colors duration-80 ease-state",
          "hover:bg-surface-hover focus:border-action-accent focus:shadow-input-focus focus:outline-none",
          "disabled:cursor-not-allowed disabled:bg-surface-sunken disabled:text-text-faint",
          className,
        )}
      >
        <span className="flex min-w-0 items-center gap-2 truncate">
          {renderValue ? (
            renderValue(selected)
          ) : selected ? (
            selected.label
          ) : (
            <span className="text-text-faint">{placeholder}</span>
          )}
        </span>
        <Icon name="chev" className="size-4 shrink-0 text-text-subtle" />
      </DropdownMenuPrimitive.Trigger>

      <DropdownMenuPrimitive.Portal>
        <DropdownMenuPrimitive.Content
          align={align}
          sideOffset={6}
          className={cn(
            "z-[1360] w-[var(--radix-dropdown-menu-trigger-width)] min-w-[240px] overflow-hidden rounded-md border border-border bg-surface-primary p-1 shadow-2",
            contentClassName,
          )}
        >
          <div className="flex items-center gap-2 border-b border-border px-2.5 py-2">
            <Icon name="search" className="size-4 shrink-0 text-text-subtle" />
            <input
              ref={inputRef}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                // ArrowDown hands off to the menu's roving focus explicitly:
                // the input is not a menu item, so Radix will not move focus
                // off it on its own and the list would be unreachable by
                // keyboard. From the first item its own handlers take over.
                if (event.key === "ArrowDown") {
                  const first = event.currentTarget
                    .closest('[role="menu"]')
                    ?.querySelector<HTMLElement>('[role="menuitem"]');
                  if (first) {
                    event.preventDefault();
                    first.focus();
                  }
                  return;
                }
                // Escape closes and Tab leaves — everything else is typing and
                // must reach the input rather than the menu's typeahead.
                if (!["Escape", "Tab"].includes(event.key)) {
                  event.stopPropagation();
                }
              }}
              placeholder={searchPlaceholder}
              aria-label={searchPlaceholder}
              className="w-full bg-transparent text-body-sm text-text-primary outline-none placeholder:text-text-subtle"
            />
          </div>

          <div className="max-h-60 overflow-y-auto py-1">
            {clearLabel ? (
              <DropdownMenuPrimitive.Item
                onSelect={() => onChange(null)}
                className={cn(
                  "flex h-8 cursor-pointer select-none items-center rounded-xs px-2.5 text-body-md outline-none",
                  "text-text-secondary data-[highlighted]:bg-surface-hover data-[highlighted]:text-text-primary",
                )}
              >
                {clearLabel}
              </DropdownMenuPrimitive.Item>
            ) : null}

            {filtered.length === 0 ? (
              <p className="px-2.5 py-4 text-center text-caption text-text-subtle">
                {options.length === 0
                  ? "Nothing to choose from."
                  : `No matches for “${query}”.`}
              </p>
            ) : (
              filtered.map((option) => (
                <DropdownMenuPrimitive.Item
                  key={option.value}
                  onSelect={() => onChange(option.value)}
                  className={cn(
                    "flex cursor-pointer select-none items-center gap-2 rounded-xs px-2.5 py-1.5 text-body-md outline-none",
                    "data-[highlighted]:bg-surface-hover",
                    option.value === value
                      ? "font-semibold text-action-accent"
                      : "text-text-primary",
                  )}
                >
                  {renderOption ? (
                    renderOption(option)
                  ) : (
                    <span className="min-w-0 flex-1">
                      <span className="block truncate">{option.label}</span>
                      {option.sublabel ? (
                        <span className="block truncate text-caption text-text-subtle">
                          {option.sublabel}
                        </span>
                      ) : null}
                    </span>
                  )}
                  {option.value === value ? (
                    <Icon name="check" className="size-3.5 shrink-0" />
                  ) : null}
                </DropdownMenuPrimitive.Item>
              ))
            )}
          </div>
        </DropdownMenuPrimitive.Content>
      </DropdownMenuPrimitive.Portal>
    </DropdownMenuPrimitive.Root>
  );
}
