import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";

type PaginationProps = {
  /** 1-based current page. */
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
  className?: string;
};

/** Windowed page list: 1 … p−1 p p+1 … n ("…" as gaps). */
function pageItems(page: number, pageCount: number): (number | "gap")[] {
  if (pageCount <= 7) {
    return Array.from({ length: pageCount }, (_, i) => i + 1);
  }
  const middle = [page - 1, page, page + 1].filter(
    (p) => p > 1 && p < pageCount,
  );
  const items: (number | "gap")[] = [1];
  if ((middle[0] ?? pageCount) > 2) items.push("gap");
  items.push(...middle);
  if ((middle[middle.length - 1] ?? 0) < pageCount - 1) items.push("gap");
  items.push(pageCount);
  return items;
}

export function Pagination({
  page,
  pageCount,
  onPageChange,
  className,
}: PaginationProps) {
  if (pageCount <= 1) return null;

  const itemClass =
    "inline-flex h-7 min-w-7 items-center justify-center rounded-sm px-1.5 text-label-sm tabular transition-colors duration-80";

  return (
    <nav aria-label="Pagination" className={cn("flex items-center gap-1", className)}>
      <button
        type="button"
        aria-label="Previous page"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
        className={cn(
          itemClass,
          "text-text-secondary hover:bg-surface-hover hover:text-text-primary",
          "disabled:pointer-events-none disabled:opacity-45",
        )}
      >
        <Icon name="arrowl" className="size-4" />
      </button>
      {pageItems(page, pageCount).map((item, index) =>
        item === "gap" ? (
          <span
            key={`gap-${index}`}
            aria-hidden
            className="px-1 text-label-sm text-text-faint"
          >
            …
          </span>
        ) : (
          <button
            key={item}
            type="button"
            aria-label={`Page ${item}`}
            aria-current={item === page ? "page" : undefined}
            onClick={() => onPageChange(item)}
            className={cn(
              itemClass,
              item === page
                ? "bg-action-accent-tint font-bold text-action-accent"
                : "text-text-secondary hover:bg-surface-hover hover:text-text-primary",
            )}
          >
            {item}
          </button>
        ),
      )}
      <button
        type="button"
        aria-label="Next page"
        disabled={page >= pageCount}
        onClick={() => onPageChange(page + 1)}
        className={cn(
          itemClass,
          "text-text-secondary hover:bg-surface-hover hover:text-text-primary",
          "disabled:pointer-events-none disabled:opacity-45",
        )}
      >
        <Icon name="arrowr" className="size-4" />
      </button>
    </nav>
  );
}
