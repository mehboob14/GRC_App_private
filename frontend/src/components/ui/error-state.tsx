import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

type ErrorStateProps = {
  title?: string;
  description?: string;
  onRetry?: () => void;
  className?: string;
};

export function ErrorState({
  title = "Something went wrong",
  description = "We couldn't load this view. Try again, or contact support if it keeps happening.",
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-start gap-3 rounded-xl border border-fail-border bg-fail-bg px-6 py-5",
        className,
      )}
    >
      <h2 className="font-display text-heading-sm text-fail-fg">{title}</h2>
      <p className="text-body-md text-fail-fg/90">{description}</p>
      {onRetry ? (
        <Button variant="destructive-2" size="sm" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}
