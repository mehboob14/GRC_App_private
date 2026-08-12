import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

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

/** DS §7.2 — floating inverse bar above the table, z bulk-bar, shadow-3. */
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
        "fixed bottom-6 left-1/2 z-bulk-bar flex -translate-x-1/2 items-center gap-3",
        "animate-toast-in rounded-md bg-surface-inverse px-4 py-2.5 shadow-3",
        className,
      )}
    >
      <span className="text-label-md font-bold tabular text-text-inverse">
        {count} {noun} selected
      </span>
      <span className="h-4 w-px bg-white/20" aria-hidden />
      {children}
      <button
        type="button"
        onClick={onClear}
        className="rounded-xs px-1.5 py-0.5 text-label-sm text-text-inverse/70 hover:bg-white/10 hover:text-text-inverse"
      >
        Clear selection
      </button>
    </div>
  );
}
