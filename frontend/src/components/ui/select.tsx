import * as SelectPrimitive from "@radix-ui/react-select";
import type { ComponentPropsWithoutRef, ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";

export const Select = SelectPrimitive.Root;
export const SelectValue = SelectPrimitive.Value;

/** DS §5.4 — same anatomy as a text input: h36, radius sm, chevron right. */
export function SelectTrigger({
  className,
  ...props
}: ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>) {
  return (
    <SelectPrimitive.Trigger
      className={cn(
        "flex h-9 w-full items-center justify-between gap-2 rounded-sm border border-border bg-surface-primary px-3",
        "text-body-md text-text-primary transition-colors duration-150 ease-state",
        "focus:border-action-accent focus:shadow-input-focus focus:outline-none focus-visible:outline-none",
        "disabled:cursor-not-allowed disabled:bg-surface-sunken disabled:text-text-faint",
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
          "z-dropdown min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-md border border-border bg-surface-primary p-1 shadow-2",
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
        "relative flex h-8 cursor-pointer select-none items-center rounded-xs px-2.5 text-body-md outline-none",
        "data-[highlighted]:bg-surface-hover data-[highlighted]:text-text-primary",
        "data-[state=checked]:font-semibold data-[state=checked]:text-action-accent",
        "data-[disabled]:pointer-events-none data-[disabled]:text-text-faint",
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
      <span className="font-sans text-label-sm text-text-secondary">
        {label}
        {optional ? (
          <span className="ml-1 font-normal text-text-faint">(optional)</span>
        ) : null}
      </span>
      {children}
    </div>
  );
}
