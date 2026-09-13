import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";

/** DS §6.1 — the six status families. Severity is a separate axis (F12). */
export type StatusFamily =
  "success" | "danger" | "warning" | "progress" | "pending" | "neutral";

/**
 * Tint fill, same-family border, same-family text. The border is what makes a
 * column of these readable at a glance: on tint alone the pale families blur
 * into the row background and a reader has to look twice to tell them apart.
 */
const pillClass: Record<StatusFamily, string> = {
  success:
    "bg-status-success-bg text-status-success-text border-status-success-border",
  danger:
    "bg-status-danger-bg text-status-danger-text border-status-danger-border",
  warning:
    "bg-status-warning-bg text-status-warning-text border-status-warning-border",
  progress:
    "bg-status-progress-bg text-status-progress-text border-status-progress-border",
  pending:
    "bg-status-pending-bg text-status-pending-text border-status-pending-border",
  neutral:
    "bg-status-neutral-bg text-status-neutral-text border-status-neutral-border",
};

const textClass: Record<StatusFamily, string> = {
  success: "text-status-success-text",
  danger: "text-status-danger-text",
  warning: "text-status-warning-text",
  progress: "text-status-progress-text",
  pending: "text-status-pending-text",
  neutral: "text-status-neutral-text",
};

const dotClass: Record<StatusFamily, string> = {
  success: "bg-status-success-base",
  danger: "bg-status-danger-base",
  warning: "bg-status-warning-base",
  progress: "bg-status-progress-base",
  pending: "bg-status-pending-base",
  neutral: "bg-status-neutral-base",
};

type StatusPillProps = {
  /** `unknown` renders help icon + word — never a bare dot (DS §6.2). */
  status: StatusFamily | "unknown";
  /** Always required: colour may never carry meaning alone (F10). */
  label: string;
  /**
   * pill — default chip on tint · inline — dot + word for dense cells ·
   * circle — 22×22 solid circle with icon for pass/fail lists.
   */
  kind?: "pill" | "inline" | "circle";
  className?: string;
};

/** DS §6.2 StatusPill anatomy. */
export function StatusPill({
  status,
  label,
  kind = "pill",
  className,
}: StatusPillProps) {
  if (status === "unknown") {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1 text-caption font-semibold text-status-neutral-text",
          className,
        )}
      >
        <Icon name="help" className="size-[13px]" />
        {label}
      </span>
    );
  }

  if (kind === "circle") {
    return (
      <span
        className={cn("inline-flex items-center gap-1.5", className)}
        title={label}
      >
        <span
          className={cn(
            "flex size-[22px] items-center justify-center rounded-full text-white",
            dotClass[status],
          )}
        >
          <Icon
            name={status === "danger" ? "x" : "check"}
            className="size-[13px]"
          />
        </span>
        <span className="sr-only">{label}</span>
      </span>
    );
  }

  if (kind === "inline") {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1.5 text-caption font-semibold",
          textClass[status],
          className,
        )}
      >
        <span className={cn("size-1.5 rounded-full", dotClass[status])} />
        {label}
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-[9px] py-[3px] text-caption font-bold",
        pillClass[status],
        className,
      )}
    >
      <span className={cn("size-1.5 rounded-full", dotClass[status])} />
      {label}
    </span>
  );
}
