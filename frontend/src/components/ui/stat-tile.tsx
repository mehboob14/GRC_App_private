import { Link } from "react-router-dom";
import { cn } from "@/lib/cn";
import { Icon, type IconName } from "@/components/ui/icon";

export type StatTone = "neutral" | "danger" | "warning" | "success" | "progress";

const ICON_TILE: Record<StatTone, string> = {
  neutral: "bg-surface-sunken text-text-secondary",
  danger: "bg-status-danger-bg text-status-danger-text",
  warning: "bg-status-warning-bg text-status-warning-text",
  success: "bg-status-success-bg text-status-success-text",
  progress: "bg-action-accent-tint text-action-accent",
};

const VALUE_TEXT: Record<StatTone, string> = {
  neutral: "text-text-primary",
  danger: "text-status-danger-text",
  warning: "text-status-warning-text",
  success: "text-status-success-text",
  progress: "text-action-accent",
};

/**
 * A headline number with its icon and label, and usually a way in: pass `to`
 * to link to the filtered list, or `onClick` for anything else.
 *
 * A zero never wears the alarm colour. "0 overdue" is good news, and painting
 * it red teaches people to ignore red.
 */
export function StatTile({
  icon,
  label,
  value,
  tone = "neutral",
  caption,
  to,
  onClick,
  className,
}: {
  icon: IconName;
  label: string;
  value: number | string;
  tone?: StatTone;
  /** One short line under the label, e.g. "3 overdue". */
  caption?: string;
  to?: string;
  onClick?: () => void;
  className?: string;
}) {
  const quiet = value === 0 || value === "0";
  const body = (
    <>
      <span
        className={cn(
          "grid size-10 shrink-0 place-items-center rounded-md",
          quiet ? ICON_TILE.neutral : ICON_TILE[tone],
        )}
      >
        <Icon name={icon} className="size-5" />
      </span>
      <span className="min-w-0">
        <span
          className={cn(
            "block font-display text-numeral-md tabular leading-tight",
            quiet ? "text-text-primary" : VALUE_TEXT[tone],
          )}
        >
          {value}
        </span>
        <span className="block truncate text-body-sm text-text-secondary">{label}</span>
        {caption ? <span className="block truncate text-caption text-text-subtle">{caption}</span> : null}
      </span>
    </>
  );

  const frame = cn(
    "flex items-center gap-3.5 rounded-lg border border-border bg-surface-primary p-4 text-left",
    className,
  );
  const interactive =
    "transition-colors duration-80 ease-state hover:border-border-strong hover:bg-surface-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent";

  if (to) {
    return (
      <Link to={to} className={cn(frame, interactive)}>
        {body}
      </Link>
    );
  }
  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={cn(frame, interactive)}>
        {body}
      </button>
    );
  }
  return <div className={frame}>{body}</div>;
}

/**
 * One line of a "needs attention" list: icon, count, what it counts. The whole
 * row is the way in when `to` or `onClick` is given.
 */
export function StatRow({
  icon,
  label,
  value,
  tone = "neutral",
  to,
  onClick,
}: {
  icon: IconName;
  label: string;
  value: number | string;
  tone?: StatTone;
  to?: string;
  onClick?: () => void;
}) {
  const quiet = value === 0 || value === "0";
  const body = (
    <>
      <span
        className={cn(
          "grid size-8 shrink-0 place-items-center rounded-md",
          quiet ? ICON_TILE.neutral : ICON_TILE[tone],
        )}
      >
        <Icon name={icon} className="size-4" />
      </span>
      <span className="min-w-0 flex-1">
        <span
          className={cn(
            "block font-display text-title-sm tabular leading-tight",
            quiet ? "text-text-primary" : VALUE_TEXT[tone],
          )}
        >
          {value}
        </span>
        <span className="block truncate text-body-sm text-text-secondary">{label}</span>
      </span>
      {to || onClick ? <Icon name="chevr" className="size-3.5 shrink-0 text-text-faint" /> : null}
    </>
  );
  const frame = "flex w-full items-center gap-3 rounded-md px-2 py-2 text-left";
  const interactive =
    "transition-colors duration-80 ease-state hover:bg-surface-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent";
  if (to) {
    return (
      <Link to={to} className={cn(frame, interactive)}>
        {body}
      </Link>
    );
  }
  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={cn(frame, interactive)}>
        {body}
      </button>
    );
  }
  return <div className={frame}>{body}</div>;
}
