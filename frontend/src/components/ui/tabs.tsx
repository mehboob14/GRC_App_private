import * as TabsPrimitive from "@radix-ui/react-tabs";
import type { ComponentPropsWithoutRef } from "react";
import { cn } from "@/lib/cn";

export const Tabs = TabsPrimitive.Root;

export function TabsList({
  className,
  ...props
}: ComponentPropsWithoutRef<typeof TabsPrimitive.List>) {
  return (
    <TabsPrimitive.List
      className={cn(
        "inline-flex w-full flex-col gap-0.5 rounded-md border border-border bg-surface-primary p-1",
        className,
      )}
      {...props}
    />
  );
}

export function TabsTrigger({
  className,
  ...props
}: ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        "inline-flex items-center rounded-sm px-3 py-2 text-left font-sans text-label-md text-text-secondary",
        "outline-none transition-colors hover:bg-surface-hover hover:text-text-primary",
        "data-[state=active]:bg-action-accent-tint data-[state=active]:text-action-accent",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
        className,
      )}
      {...props}
    />
  );
}

export function TabsContent({
  className,
  ...props
}: ComponentPropsWithoutRef<typeof TabsPrimitive.Content>) {
  return (
    <TabsPrimitive.Content
      className={cn("outline-none focus-visible:outline-none", className)}
      {...props}
    />
  );
}
