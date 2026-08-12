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
