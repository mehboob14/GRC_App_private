import * as DropdownMenuPrimitive from "@radix-ui/react-dropdown-menu";
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
  className?: string;
};

/**
 * Toolbar filter facet (DS §2.4 active-chip tokens, dropdown per §7.1).
 * Resting chip is neutral; with selections it takes accent tint + border
 * and shows the count. The menu offers checkbox options and a clear row.
 */
export function FilterFacet({
  label,
  options,
  values,
  onChange,
  className,
}: FilterFacetProps) {
  const active = values.length > 0;

  const toggle = (value: string, checked: boolean) => {
    onChange(
      checked ? [...values, value] : values.filter((v) => v !== value),
    );
  };

  return (
    <DropdownMenuPrimitive.Root>
      <DropdownMenuPrimitive.Trigger
        className={cn(
          "inline-flex h-8 items-center gap-1.5 rounded-sm border px-2.5 font-sans text-label-sm",
          "transition-colors duration-80 ease-state",
          active
            ? "border-action-accent-border bg-action-accent-tint text-action-accent"
            : "border-border bg-surface-primary text-text-secondary hover:bg-surface-hover",
          className,
        )}
      >
        <Icon name="filter" className="size-3.5" />
        {label}
        {active ? (
          <span className="tabular font-bold">{values.length}</span>
        ) : null}
        <Icon name="chev" className="size-3.5" />
      </DropdownMenuPrimitive.Trigger>
      <DropdownMenuPrimitive.Portal>
        <DropdownMenuPrimitive.Content
          sideOffset={6}
          align="start"
          className="z-dropdown min-w-[180px] overflow-hidden rounded-md border border-border bg-surface-primary p-1 shadow-2"
        >
          {options.map((option) => (
            <DropdownMenuPrimitive.CheckboxItem
              key={option.value}
              checked={values.includes(option.value)}
              onCheckedChange={(checked) => toggle(option.value, checked === true)}
              onSelect={(event) => event.preventDefault()}
              className={cn(
                "relative flex h-8 cursor-pointer select-none items-center gap-2 rounded-xs pl-7 pr-2.5 text-body-md outline-none",
                "text-text-primary data-[highlighted]:bg-surface-hover",
                "data-[disabled]:pointer-events-none data-[disabled]:text-text-faint",
              )}
            >
              <DropdownMenuPrimitive.ItemIndicator className="absolute left-2 text-action-accent">
                <Icon name="check" className="size-3.5" strokeWidth={2.5} />
              </DropdownMenuPrimitive.ItemIndicator>
              {option.label}
            </DropdownMenuPrimitive.CheckboxItem>
          ))}
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
