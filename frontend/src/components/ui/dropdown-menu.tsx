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
          "z-50 min-w-[220px] overflow-hidden rounded-md border border-border bg-surface-primary p-1 shadow-2",
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
  ...props
}: ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Item> & {
  inset?: boolean;
}) {
  return (
    <DropdownMenuPrimitive.Item
      className={cn(
        "relative flex cursor-pointer select-none items-center gap-2 rounded-sm px-2.5 py-2 text-body-md outline-none",
        "text-text-primary data-[highlighted]:bg-action-accent-tint data-[highlighted]:text-action-accent",
        "data-[disabled]:pointer-events-none data-[disabled]:text-text-subtle",
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
