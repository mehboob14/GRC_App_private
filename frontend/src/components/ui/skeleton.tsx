import { cn } from "@/lib/cn";

type SkeletonProps = {
  className?: string;
  /**
   * block — content bones (rows, cards, avatars) · bar — thin header bars
   * (h8, radius 4). DS §7.4: bones mirror the real layout, reserve exact
   * heights via className.
   */
  tone?: "block" | "bar";
};

/**
 * Shimmer 1.4s linear; prefers-reduced-motion renders a static bone
 * (tokens.css). Show only after 400ms and hold 300ms — callers own timing.
 */
export function Skeleton({ className, tone = "block" }: SkeletonProps) {
  return (
    <div
      aria-hidden
      className={cn(
        "animate-shimmer",
        tone === "bar"
          ? "h-2 rounded-2xs bg-gradient-to-r from-border via-surface-hover to-border"
          : "rounded-sm bg-gradient-to-r from-surface-hover via-surface-sunken to-surface-hover",
        className,
      )}
    />
  );
}

type TableSkeletonProps = {
  rows?: number;
  /** Must match the density of the table that replaces it — no layout shift. */
  density?: "comfortable" | "standard" | "compact";
  className?: string;
};

/** DS §7.4 — bones mirror the real table: sunken header, row-height blocks. */
export function TableSkeleton({
  rows = 8,
  density = "comfortable",
  className,
}: TableSkeletonProps) {
  const rowHeight = {
    comfortable: "h-14",
    standard: "h-12",
    compact: "h-10",
  }[density];
  return (
    <div
      aria-hidden
      className={cn(
        "overflow-hidden rounded-lg border border-border bg-surface-primary",
        className,
      )}
    >
      <div
        className={cn(
          "flex items-center gap-8 border-b border-border bg-surface-sunken px-4",
          density === "compact" ? "h-9" : "h-10",
        )}
      >
        <Skeleton tone="bar" className="w-24" />
        <Skeleton tone="bar" className="w-16" />
        <Skeleton tone="bar" className="w-20" />
      </div>
      {Array.from({ length: rows }, (_, index) => (
        <div
          key={index}
          className={cn(
            "flex items-center gap-4 border-b border-border px-4 last:border-b-0",
            rowHeight,
          )}
        >
          <Skeleton className="size-6 rounded-full" />
          <Skeleton className="h-3 w-40" />
          <Skeleton className="h-5 w-20 rounded-full" />
          <Skeleton className="ml-auto h-3 w-28" />
        </div>
      ))}
    </div>
  );
}
