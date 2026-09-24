import * as DialogPrimitive from "@radix-ui/react-dialog";
import type { ComponentPropsWithoutRef, ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";

/**
 * DS §7.1 modal — focused create/edit and confirmations ("commit").
 * Fixed widths 480/600/720; beyond 720 or 70vh the content wants a page.
 */
export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;

const widths = {
  sm: "w-[min(480px,calc(100vw-2rem))]",
  md: "w-[min(600px,calc(100vw-2rem))]",
  lg: "w-[min(720px,calc(100vw-2rem))]",
  /**
   * Past the DS's 720, for the one shape that needs it: two columns of people,
   * roles and groups side by side. At 720 each column is narrow enough that a
   * full name wraps and a list of ten looks like a wall, which is exactly the
   * case a picker has to stay readable in.
   */
  xl: "w-[min(920px,calc(100vw-2rem))]",
  /**
   * The full record form: a narrative column beside a panel of classification
   * and ownership. Two readable columns need the room, and the alternative is
   * the same form as one tall scroll, which is what a page is for.
   */
  "2xl": "w-[min(1080px,calc(100vw-2rem))]",
} as const;

type DialogContentProps = ComponentPropsWithoutRef<
  typeof DialogPrimitive.Content
> & {
  size?: keyof typeof widths;
  /**
   * Scroll a `<DialogBody>` instead of the whole dialog, which keeps the header
   * and footer in place — the Drawer arrangement. Opt-in: without it the dialog
   * scrolls as one block, which is right for short content and is what every
   * dialog written before this did.
   */
  scrollBody?: boolean;
};

export function DialogContent({
  className,
  children,
  size = "sm",
  scrollBody = false,
  ...props
}: DialogContentProps) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay
        className={cn(
          "fixed inset-0 z-modal bg-black/50 backdrop-blur-sm",
          "data-[state=open]:animate-overlay-in data-[state=closed]:animate-overlay-out",
        )}
      />
      <DialogPrimitive.Content
        className={cn(
          "fixed left-1/2 top-1/2 z-modal -translate-x-1/2 -translate-y-1/2",
          "max-h-[70vh] rounded-xl border border-border bg-surface-primary p-6 shadow-4",
          scrollBody ? "flex flex-col overflow-hidden" : "overflow-y-auto",
          "focus:outline-none",
          "data-[state=open]:animate-modal-in data-[state=closed]:animate-modal-out",
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
            aria-label="Close"
          >
            <Icon name="x" className="size-4 text-text-subtle" />
          </Button>
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

export function DialogHeader({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("mb-4 flex flex-col gap-1 pr-8", className)}
      {...props}
    />
  );
}

export function DialogTitle({
  className,
  ...props
}: ComponentPropsWithoutRef<typeof DialogPrimitive.Title>) {
  return (
    <DialogPrimitive.Title
      className={cn(
        "font-display text-heading-md text-text-primary",
        className,
      )}
      {...props}
    />
  );
}

export function DialogDescription({
  className,
  ...props
}: ComponentPropsWithoutRef<typeof DialogPrimitive.Description>) {
  return (
    <DialogPrimitive.Description
      className={cn("text-body-md text-text-secondary", className)}
      {...props}
    />
  );
}

export function DialogFooter({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={cn("mt-6 flex shrink-0 justify-end gap-2", className)}>
      {children}
    </div>
  );
}

/**
 * The scrolling middle of a `scrollBody` dialog. Put the fields in here and the
 * confirm button stays reachable however tall the form gets.
 *
 * The negative margins bleed the scroll area through the content's `p-6` so the
 * scrollbar rides the dialog edge rather than floating inside the padding, and
 * the padding is re-applied inside.
 */
export function DialogBody({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={cn("-mx-6 min-h-0 flex-1 overflow-y-auto px-6", className)}>
      {children}
    </div>
  );
}
