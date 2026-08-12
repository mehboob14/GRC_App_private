import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type EmptyStateProps = {
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
  comingSoon?: boolean;
};

export function EmptyState({
  title,
  description,
  action,
  className,
  comingSoon,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-surface-primary px-8 py-16 text-center",
        className,
      )}
    >
      {comingSoon ? (
        <span className="mb-3 rounded-full bg-action-accent-tint px-2.5 py-1 type-overline text-action-accent">
          Coming soon
        </span>
      ) : null}
      <h2 className="font-display text-heading-sm text-text-primary">{title}</h2>
      {description ? (
        <p className="mt-2 max-w-md text-body-md text-text-secondary">{description}</p>
      ) : null}
      {action ? <div className="mt-6">{action}</div> : null}
    </div>
  );
}
