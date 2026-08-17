import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";

type BulkActionBarProps = {
  /** Exact selection count — bulk destructives must name it (§7.2). */
  count: number;
  /** Noun for the count line, e.g. "controls". */
  noun: string;
  onClear: () => void;
  /** Action buttons; destructive actions go last. */
  children: ReactNode;
  className?: string;
};

/**
 * Floating bar over the table while rows are selected.
 *
 * Surface, not inverse: an inverse slab was the only dark element in the
 * product and read as a foreign overlay. It is now the same elevated surface
 * as a dialog or popover — `surface-primary` on a hairline border with
 * shadow-3 — so a selection reads as part of the page it belongs to.
 */
export function BulkActionBar({
  count,
  noun,
  onClear,
  children,
  className,
}: BulkActionBarProps) {
  if (count === 0) return null;

  return (
    <div
      role="toolbar"
      aria-label={`Bulk actions for ${count} selected ${noun}`}
      className={cn(
        "fixed bottom-6 left-1/2 z-bulk-bar -translate-x-1/2",
        "flex max-w-[calc(100vw-2rem)] flex-wrap items-center gap-1.5",
        "animate-toast-in rounded-lg border border-border bg-surface-primary px-2.5 py-2 shadow-3",
        className,
      )}
    >
      <span className="inline-flex shrink-0 items-center gap-2 rounded-md bg-action-accent-tint px-2.5 py-1">
        <Icon name="check" className="size-3.5 text-action-accent" strokeWidth={3} />
        <span className="tabular text-label-sm font-bold text-action-accent">
          {count} {noun} selected
        </span>
      </span>

      <span className="mx-0.5 h-5 w-px shrink-0 bg-border" aria-hidden />

      {children}

      <span className="mx-0.5 h-5 w-px shrink-0 bg-border" aria-hidden />

      <Button variant="ghost" size="sm" onClick={onClear} className="shrink-0">
        Clear
      </Button>
    </div>
  );
}
