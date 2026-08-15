import { Slot } from "@radix-ui/react-slot";
import { cn } from "@/lib/cn";
import type { HTMLAttributes } from "react";

/**
 * `asChild` renders the card chrome onto the child element — a card that is
 * itself the click target becomes a real <button>, so Enter/Space, focus and
 * keyboard reach come from the platform rather than a keydown handler.
 */
export function Card({
  className,
  asChild = false,
  ...props
}: HTMLAttributes<HTMLDivElement> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "div";
  return (
    <Comp
      className={cn(
        // Static cards are border-only — shadows mean "floating" (§4.4).
        "rounded-lg border border-border bg-surface-primary",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-1 px-5 pt-5", className)} {...props} />;
}

export function CardTitle({
  className,
  ...props
}: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={cn("font-sans text-title-md text-text-primary", className)}
      {...props}
    />
  );
}

export function CardDescription({
  className,
  ...props
}: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p className={cn("text-body-sm text-text-secondary", className)} {...props} />
  );
}

export function CardContent({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-5 py-4", className)} {...props} />;
}
