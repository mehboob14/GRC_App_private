import { cn } from "@/lib/cn";
import { TIER_META } from "../tokens";
import { TIER_TONE } from "./tier-tone";

/**
 * A tier, in the one colour it has everywhere.
 *
 * `solid` is the chip for headers and summaries. `dot` is for dense rows, where
 * a column of solid chips would shout louder than the data around it.
 */
export function TierBadge({
  tier,
  label,
  variant = "solid",
  className,
}: {
  tier: string | null | undefined;
  /** Replaces the tier word, e.g. "Medium tier" in a header. */
  label?: string;
  variant?: "solid" | "dot";
  className?: string;
}) {
  const tone = tier ? TIER_TONE[tier] : undefined;
  const text = label ?? (tier ? (TIER_META[tier]?.label ?? tier) : "Not tiered");

  if (variant === "dot") {
    return (
      <span className={cn("inline-flex items-center gap-1.5 text-body-sm", className)}>
        <span
          className={cn("size-2 shrink-0 rounded-full", tone ? tone.fill : "bg-border-strong")}
          aria-hidden
        />
        <span className={tone ? "text-text-primary" : "text-text-subtle"}>{text}</span>
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-xs px-[7px] py-[3px] font-sans text-caption font-extrabold",
        tone ? cn(tone.fill, "text-white") : "border border-border bg-surface-sunken text-text-subtle",
        className,
      )}
    >
      {text}
    </span>
  );
}
