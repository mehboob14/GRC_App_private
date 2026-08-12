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
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-bg-elevated px-8 py-16 text-center",
        className,
      )}
    >
      {comingSoon ? (
        <span className="mb-3 rounded-full bg-accent-tint px-2.5 py-1 type-overline text-accent">
          Coming soon
        </span>
      ) : null}
      <h2 className="font-display text-heading-sm text-text">{title}</h2>
      {description ? (
        <p className="mt-2 max-w-md text-body-md text-text-muted">{description}</p>
      ) : null}
      {action ? <div className="mt-6">{action}</div> : null}
    </div>
  );
}
