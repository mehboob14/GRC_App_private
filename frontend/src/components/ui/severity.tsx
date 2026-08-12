import { cn } from "@/lib/cn";

/**
 * Severity is a separate token axis from workflow status (F12): it answers
 * "how bad", status answers "where in the lifecycle". Never restyle one as
 * the other.
 */
export type Severity = "critical" | "high" | "medium" | "low";

const fillClass: Record<Severity, string> = {
  critical: "bg-severity-critical",
  high: "bg-severity-high",
  medium: "bg-severity-medium",
  low: "bg-severity-low",
};

/** Label colour for text placed beside the chip (DS §2.6). */
export const severityTextClass: Record<Severity, string> = {
  critical: "text-severity-critical",
  high: "text-severity-high",
  medium: "text-severity-medium",
  low: "text-status-neutral-text",
};

type SeverityChipProps = {
  severity: Severity;
  /** The score or word inside the chip — a bare coloured chip is banned. */
  label: string;
  className?: string;
};

/** DS §2.6 — solid fill, white 800-weight 11px, padding 3×7, radius 6. */
export function SeverityChip({ severity, label, className }: SeverityChipProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-xs px-[7px] py-[3px] font-sans text-caption font-extrabold text-white",
        fillClass[severity],
        className,
      )}
    >
      {label}
    </span>
  );
}

/** DS §2.6 — Known-Exploited-Vulnerability badge (9px is board-specified). */
export function KevBadge({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-2xs bg-severity-critical px-[5px] py-px font-sans text-[9px] font-extrabold tracking-[0.27px] text-white",
        className,
      )}
    >
      KEV
    </span>
  );
}
