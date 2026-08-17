import * as DropdownMenuPrimitive from "@radix-ui/react-dropdown-menu";
import type { ComponentPropsWithoutRef, ReactNode } from "react";
import { cn } from "@/lib/cn";

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
