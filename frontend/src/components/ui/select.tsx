import * as SelectPrimitive from "@radix-ui/react-select";
import type { ComponentPropsWithoutRef, ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";

export const Select = SelectPrimitive.Root;
export const SelectValue = SelectPrimitive.Value;

export function SelectTrigger({
  className,
  ...props
}: ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>) {
  return (
    <SelectPrimitive.Trigger
      className={cn(
        "flex h-9 w-full items-center justify-between gap-2 rounded-md border border-border bg-surface-primary px-3",
        "text-body-md text-text-primary outline-none",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
        "disabled:cursor-not-allowed disabled:opacity-60",
        className,
      )}
      {...props}
    >
      <SelectPrimitive.Value />
      <SelectPrimitive.Icon>
        <Icon name="chev" className="size-4 text-text-subtle" />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  );
}

export function SelectContent({
  className,
  children,
  ...props
}: ComponentPropsWithoutRef<typeof SelectPrimitive.Content>) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        position="popper"
        sideOffset={4}
        className={cn(
          "z-50 min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-md border border-border bg-surface-primary p-1 shadow-2",
          className,
        )}
        {...props}
      >
        <SelectPrimitive.Viewport>{children}</SelectPrimitive.Viewport>
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  );
}

export function SelectItem({
  className,
  children,
  ...props
}: ComponentPropsWithoutRef<typeof SelectPrimitive.Item>) {
  return (
    <SelectPrimitive.Item
      className={cn(
        "relative flex cursor-pointer select-none items-center rounded-sm px-2.5 py-2 text-body-md outline-none",
        "data-[highlighted]:bg-action-accent-tint data-[highlighted]:text-action-accent",
        "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        className,
      )}
      {...props}
    >
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
    </SelectPrimitive.Item>
  );
}

export function SelectField({
  label,
  children,
  optional,
}: {
  label: string;
  children: ReactNode;
  optional?: boolean;
}) {
  return (
    <div className="flex w-full flex-col gap-1.5">
      <span className="font-sans text-label-sm text-text-primary">
        {label}
        {optional ? (
          <span className="ml-1 font-normal text-text-subtle">(optional)</span>
        ) : null}
      </span>
      {children}
    </div>
  );
}
