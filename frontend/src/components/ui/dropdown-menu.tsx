import * as DropdownMenuPrimitive from "@radix-ui/react-dropdown-menu";
import type { ComponentPropsWithoutRef, ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";

export const DropdownMenu = DropdownMenuPrimitive.Root;
export const DropdownMenuTrigger = DropdownMenuPrimitive.Trigger;
export const DropdownMenuPortal = DropdownMenuPrimitive.Portal;

export function DropdownMenuContent({
  className,
  sideOffset = 6,
  ...props
}: ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Content>) {
  return (
    <DropdownMenuPrimitive.Portal>
      <DropdownMenuPrimitive.Content
        sideOffset={sideOffset}
        className={cn(
          // Above modal/drawer so a menu opened from within one floats over it.
          "z-[1360] min-w-[220px] overflow-hidden rounded-md border border-border bg-surface-primary p-1 shadow-2",
          className,
        )}
        {...props}
      />
    </DropdownMenuPrimitive.Portal>
  );
}

export function DropdownMenuItem({
  className,
  inset,
  variant = "default",
  ...props
}: ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Item> & {
  inset?: boolean;
  /** danger — destructive rows; place them last in the menu (§7.1). */
  variant?: "default" | "danger";
}) {
  return (
    <DropdownMenuPrimitive.Item
      className={cn(
        "relative flex h-8 cursor-pointer select-none items-center gap-2 rounded-xs px-2.5 text-body-md outline-none",
        variant === "danger"
          ? "text-status-danger-text data-[highlighted]:bg-action-danger-tint"
          : "text-text-primary data-[highlighted]:bg-surface-hover",
        "data-[disabled]:pointer-events-none data-[disabled]:text-text-faint",
        inset && "pl-8",
        className,
      )}
      {...props}
    />
  );
}

export function DropdownMenuCheckboxItem({
  className,
  children,
  checked,
  onCheckedChange,
  ...props
}: ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.CheckboxItem>) {
  return (
    <DropdownMenuPrimitive.CheckboxItem
      checked={checked}
      onCheckedChange={onCheckedChange}
      // Keep the menu open while toggling several columns in a row.
      onSelect={(event) => event.preventDefault()}
      className={cn(
        "relative flex h-8 cursor-pointer select-none items-center gap-2 rounded-xs py-1 pl-8 pr-2.5 text-body-md text-text-primary outline-none",
        "data-[highlighted]:bg-surface-hover",
        "data-[disabled]:pointer-events-none data-[disabled]:text-text-faint",
        className,
      )}
      {...props}
    >
      <span className="absolute left-2 flex size-4 items-center justify-center">
        <DropdownMenuPrimitive.ItemIndicator>
          <Icon name="check" className="size-3.5" />
        </DropdownMenuPrimitive.ItemIndicator>
      </span>
      {children}
    </DropdownMenuPrimitive.CheckboxItem>
  );
}


export function DropdownMenuLabel({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <DropdownMenuPrimitive.Label
      className={cn("px-2.5 py-1.5 type-overline", className)}
    >
      {children}
    </DropdownMenuPrimitive.Label>
  );
}

export function DropdownMenuSeparator({ className }: { className?: string }) {
  return (
    <DropdownMenuPrimitive.Separator
      className={cn("my-1 h-px bg-border", className)}
    />
  );
}
