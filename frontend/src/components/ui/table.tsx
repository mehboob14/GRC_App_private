import {
  createContext,
  useContext,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type ReactNode,
  type TdHTMLAttributes,
  type ThHTMLAttributes,
} from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";

/**
 * DS §6.3 — one table system, three densities.
 * comfortable 56 (entity tables) · standard 48 (logs) · compact 40 (trails,
 * drawers; header drops 40 → 36).
 */
export type TableDensity = "comfortable" | "standard" | "compact";

const TableDensityContext = createContext<TableDensity>("comfortable");

/** TR renders in both sections; only body rows get row height and hover. */
const TableSectionContext = createContext<"head" | "body">("body");

const rowHeight: Record<TableDensity, string> = {
  comfortable: "h-14",
  standard: "h-12",
  compact: "h-10",
};

type TableProps = HTMLAttributes<HTMLTableElement> & {
  density?: TableDensity;
  /**
   * Controls that belong to the table itself (Columns, Export), rendered as a
   * bar across the top of the table card. They sit OUTSIDE the horizontal
   * scroll area, so they stay put while the columns scroll under them.
   */
  actions?: ReactNode;
};

export function Table({ className, density = "comfortable", actions, ...props }: TableProps) {
  return (
    <TableDensityContext.Provider value={density}>
      <div
        className={cn(
          "w-full overflow-hidden rounded-lg border border-border bg-surface-primary",
          className,
        )}
      >
        {actions ? (
          <div className="flex flex-wrap items-center justify-end gap-2 border-b border-border px-3 py-2">
            {actions}
          </div>
        ) : null}
        <div className="w-full overflow-x-auto">
          <table className="w-full border-collapse text-left" {...props} />
        </div>
      </div>
    </TableDensityContext.Provider>
  );
}

export function THead({
  className,
  ...props
}: HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <TableSectionContext.Provider value="head">
      <thead
        className={cn(
          // Sticky within a scrolling wrapper; inert when the page scrolls.
          "sticky top-0 z-sticky-table border-b border-border bg-surface-sunken",
          className,
        )}
        {...props}
      />
    </TableSectionContext.Provider>
  );
}

export function TBody({
  className,
  ...props
}: HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <TableSectionContext.Provider value="body">
      <tbody className={cn("divide-y divide-border", className)} {...props} />
    </TableSectionContext.Provider>
  );
}

export function TR({
  className,
  selected,
  ...props
}: HTMLAttributes<HTMLTableRowElement> & { selected?: boolean }) {
  const density = useContext(TableDensityContext);
  const section = useContext(TableSectionContext);

  if (section === "head") {
    return (
      <tr
        className={cn(density === "compact" ? "h-9" : "h-10", className)}
        {...props}
      />
    );
  }

  return (
    <tr
      aria-selected={selected || undefined}
      className={cn(
        rowHeight[density],
        "bg-surface-primary transition-colors duration-80",
        selected ? "bg-action-accent-tint" : "hover:bg-surface-hover",
        className,
      )}
      {...props}
    />
  );
}

type THProps = ThHTMLAttributes<HTMLTableCellElement> & {
  sortable?: boolean;
  sorted?: "asc" | "desc" | false;
  onSort?: () => void;
  /** Right-aligns the column (sortable numerics, F11). */
  numeric?: boolean;
};

export function TH({
  className,
  sortable,
  sorted,
  onSort,
  numeric,
  children,
  ...props
}: THProps) {
  const density = useContext(TableDensityContext);
  // Uppercase micro-label, per the reference design, but at text-secondary
  // rather than the old text-faint. Only the COLOUR was ever the defect:
  // faint on surface-sunken measured 2.51:1 light and 3.49:1 dark, failing AA
  // and even the 3:1 non-text floor. Secondary measures 7.48:1 and 6.42:1.
  const content = (
    <span
      className={cn(
        "inline-flex items-center gap-1 font-sans text-overline uppercase text-text-secondary transition-colors duration-80",
        sortable && "group-hover:text-text-primary",
        numeric && "justify-end",
      )}
    >
      {children}
      {sortable ? (
        <Icon
          name="chev"
          className={cn(
            "size-[13px] text-text-subtle",
            sorted === "asc" && "rotate-180 text-text-primary",
            sorted === "desc" && "text-text-primary",
          )}
        />
      ) : null}
    </span>
  );

  const cellClass = cn(
    density === "compact" ? "h-9" : "h-10",
    "px-4 align-middle",
    numeric && "text-right",
    className,
  );

  if (sortable) {
    return (
      <th
        className={cellClass}
        aria-sort={
          sorted === "asc"
            ? "ascending"
            : sorted === "desc"
              ? "descending"
              : undefined
        }
        {...props}
      >
        <button
          type="button"
          onClick={onSort}
          className="group inline-flex items-center gap-1 rounded-2xs"
        >
          {content}
        </button>
      </th>
    );
  }

  return (
    <th className={cellClass} {...props}>
      {content}
    </th>
  );
}

type TDProps = TdHTMLAttributes<HTMLTableCellElement> & {
  /** Right-align + tabular numerals (F11). */
  numeric?: boolean;
};

export function TD({ className, numeric, ...props }: TDProps) {
  return (
    <td
      className={cn(
        "px-4 align-middle text-body-md text-text-primary",
        numeric && "tabular text-right",
        className,
      )}
      {...props}
    />
  );
}

/** DS §5.3 icon-only 28 for in-row actions — callers must pass aria-label. */
export function TableIconButton({
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      className={cn(
        "inline-flex size-7 items-center justify-center rounded-sm text-text-subtle transition-colors duration-80 hover:bg-surface-hover hover:text-text-primary",
        className,
      )}
      {...props}
    />
  );
}

export function TableEmpty({ children }: { children: ReactNode }) {
  return (
    <tr>
      <td
        colSpan={99}
        className="px-4 py-12 text-center text-body-md text-text-secondary"
      >
        {children}
      </td>
    </tr>
  );
}
