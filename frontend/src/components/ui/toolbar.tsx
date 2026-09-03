import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/**
 * One row: search, filters, actions. It stretches; it never scrolls the page
 * sideways.
 *
 * Sizing contract, owned here so no call site restates it:
 *   search   min-w-0 max-w-[420px] flex-1 basis-56  absorbs slack, compresses
 *   filters  natural width; FilterFacet truncates its own value
 *   actions  ml-auto shrink-0                       pinned right, never clipped
 *
 * flex-wrap is the last resort, not the layout. Below roughly 640px the row
 * wraps to a second line; the alternative is overflowing the app shell's
 * `overflow-auto` main and putting a horizontal scrollbar on the whole page.
 * Nothing here is hidden at a breakpoint.
 *
 * Eight registers hand-rolled this row with seven different search widths
 * (w-64, w-56, w-full sm:w-64, w-full sm:w-72, w-full min-w-0 sm:w-64 lg:w-72,
 * min-w-[220px] flex-1, and a min-w-[240px] wrapper div), and two of them had
 * no flex-wrap at all.
 */
export function Toolbar({
  search,
  searchLabel = "Filter",
  children,
  actions,
  className,
}: {
  /** A <SearchInput /> with NO width className - the slot owns the width. */
  search?: ReactNode;
  /** aria-label for the search landmark, e.g. "Filter controls". */
  searchLabel?: string;
  /** Filter facets, and the ghost "Clear filters" button. */
  children?: ReactNode;
  /** Primary and secondary buttons, pinned right. */
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mb-3 mt-4 flex flex-wrap items-center gap-2", className)}>
      {search ? (
        <div
          role="search"
          aria-label={searchLabel}
          className="min-w-0 max-w-[420px] flex-1 basis-56"
        >
          {search}
        </div>
      ) : null}
      {children}
      {actions ? (
        <div className="ml-auto flex shrink-0 items-center gap-2">{actions}</div>
      ) : null}
    </div>
  );
}
