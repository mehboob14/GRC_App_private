import * as DialogPrimitive from "@radix-ui/react-dialog";
import type { ComponentPropsWithoutRef, HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";

/**
 * DS §7.1 drawer — quick-look a row without losing list context ("peek").
 * Fixed widths 480/560, right side, scrim .45 + blur, pinned footer.
 * Focus is trapped and restored by Radix; Esc closes.
 */
export const Drawer = DialogPrimitive.Root;
export const DrawerTrigger = DialogPrimitive.Trigger;
export const DrawerClose = DialogPrimitive.Close;

const widths = {
  md: "w-[480px]",
  lg: "w-[560px]",
  /** A dense multi-column form (e.g. the asset editor) needs real width to
   *  keep fields two-across without wrapping every label. */
  xl: "w-[780px]",
} as const;

type DrawerContentProps = ComponentPropsWithoutRef<
  typeof DialogPrimitive.Content
> & {
  size?: keyof typeof widths;
};

export function DrawerContent({
  className,
  children,
  size = "md",
  ...props
}: DrawerContentProps) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay
        className={cn(
          "fixed inset-0 z-drawer bg-black/45 backdrop-blur-sm",
          "data-[state=open]:animate-overlay-in data-[state=closed]:animate-overlay-out",
        )}
      />
      <DialogPrimitive.Content
        className={cn(
          "fixed inset-y-0 right-0 z-drawer flex max-w-[calc(100vw-2rem)] flex-col",
          "border-l border-border bg-surface-primary shadow-3 focus:outline-none",
          "data-[state=open]:animate-drawer-in data-[state=closed]:animate-drawer-out",
          widths[size],
          className,
        )}
        {...props}
      >
        {children}
        <DialogPrimitive.Close asChild>
          <Button
            variant="ghost"
            size="icon-sm"
            className="absolute right-3 top-3"
            aria-label="Close panel"
          >
            <Icon name="x" className="size-4 text-text-subtle" />
          </Button>
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

export function DrawerHeader({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "flex shrink-0 flex-col gap-1 border-b border-border px-5 py-4 pr-12",
        className,
      )}
      {...props}
    />
  );
}

export function DrawerTitle({
  className,
  ...props
}: ComponentPropsWithoutRef<typeof DialogPrimitive.Title>) {
  return (
    <DialogPrimitive.Title
      className={cn("font-display text-heading-md text-text-primary", className)}
      {...props}
    />
  );
}

export function DrawerDescription({
  className,
  ...props
}: ComponentPropsWithoutRef<typeof DialogPrimitive.Description>) {
  return (
    <DialogPrimitive.Description
      className={cn("text-body-sm text-text-subtle", className)}
      {...props}
    />
  );
}

/** Scrollable middle region between header and pinned footer. */
export function DrawerBody({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("min-h-0 flex-1 overflow-y-auto px-5 py-4", className)}
      {...props}
    />
  );
}

/** Pinned footer — actions stay visible however long the body is. */
export function DrawerFooter({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={cn(
        "flex shrink-0 justify-end gap-2 border-t border-border px-5 py-4",
        className,
      )}
    >
      {children}
    </div>
  );
}
