import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

const variants = {
  neutral: "bg-na-bg text-text-muted border-transparent",
  role: "bg-accent-tint text-accent border-transparent",
  count: "bg-fail-bg text-fail-fg border-transparent",
  countWarn: "bg-review-bg text-review-fg border-transparent",
  statusPass: "bg-pass-bg text-pass-fg border-transparent",
  statusFail: "bg-fail-bg text-fail-fg border-fail-border border",
  statusReview: "bg-review-bg text-review-fg border-transparent",
  statusPending: "bg-na-bg text-pending border-transparent",
} as const;

export type BadgeVariant = keyof typeof variants;

type BadgeProps = {
  children: ReactNode;
  variant?: BadgeVariant;
  className?: string;
};

export function Badge({
  children,
  variant = "neutral",
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-1.5 py-px font-sans text-[10px] font-bold leading-none",
        variants[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
