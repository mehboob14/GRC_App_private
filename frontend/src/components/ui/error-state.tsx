import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";
import { cn } from "@/lib/cn";

type ErrorStateProps = {
  title?: string;
  description?: string;
  onRetry?: () => void;
  /** Support reference shown under the message (DS §7.5 "Failed"). */
  referenceId?: string;
  className?: string;
};

/**
 * Full-view failed state (a data view that could not load). For form-level
 * problems inside a working view use ErrorBanner instead.
 */
export function ErrorState({
  title = "Couldn’t load this view",
  description = "The request failed. Retry, or contact support if it keeps happening.",
  onRetry,
  referenceId,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center justify-center rounded-md border border-border bg-surface-sunken px-8 py-14 text-center",
        className,
      )}
    >
      <span className="mb-3 flex size-10 items-center justify-center rounded-md bg-status-danger-bg">
        <Icon name="alert" className="size-5 text-status-danger-base" />
      </span>
      <h2 className="font-display text-title-md text-text-primary">{title}</h2>
      <p className="mt-1.5 max-w-md text-body-sm text-text-subtle">
        {description}
      </p>
      {onRetry ? (
        <Button variant="secondary" size="sm" className="mt-4" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
      {referenceId ? (
        <p className="mt-3 text-caption text-text-subtle">
          Reference: <span className="tabular">{referenceId}</span>
        </p>
      ) : null}
    </div>
  );
}
