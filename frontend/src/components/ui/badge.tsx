import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/**
 * Small count / role / framework chips. Workflow status words belong on
 * StatusPill — the status* variants here exist for count-style usage only
 * and follow the same F7 families.
 */
const variants = {
  neutral: "bg-status-neutral-bg text-status-neutral-text border-transparent",
  role: "bg-action-accent-tint text-action-accent border-transparent",
  count: "bg-status-danger-bg text-status-danger-text border-transparent",
  countWarn: "bg-status-warning-bg text-status-warning-text border-transparent",
  statusPass: "bg-status-success-bg text-status-success-text border-transparent",
  statusFail: "bg-status-danger-bg text-status-danger-text border-status-danger-border border",
  statusReview: "bg-status-warning-bg text-status-warning-text border-transparent",
  statusPending: "bg-status-pending-bg text-status-pending-text border-transparent",
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
