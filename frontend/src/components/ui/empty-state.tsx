import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/button";
import { Icon, type IconName } from "@/components/ui/icon";

type EmptyStateProps = {
  title: string;
  /** Say what happened and what to do next; name active filters (§7.5). */
  description?: string;
  icon?: IconName;
  /**
   * no-data — first use, offer the primary action · no-match —
   * filtered-empty, keep the toolbar visible and offer Clear filters.
   */
  variant?: "no-data" | "no-match";
  /** Primary action for no-data (one action only). */
  action?: ReactNode;
  /** Renders the secondary "Clear filters" action for no-match. */
  onClearFilters?: () => void;
  className?: string;
  comingSoon?: boolean;
};

/** DS §7.5 empty-state anatomy: sunken panel, icon tile 40, one action. */
export function EmptyState({
  title,
  description,
  icon = "search",
  variant = "no-data",
  action,
  onClearFilters,
  className,
  comingSoon,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-md border border-border bg-surface-sunken px-8 py-14 text-center",
        className,
      )}
    >
      {comingSoon ? (
        <span className="mb-3 rounded-full bg-action-accent-tint px-2.5 py-1 type-overline text-action-accent">
          Coming soon
        </span>
      ) : (
        <span className="mb-3 flex size-10 items-center justify-center rounded-md bg-surface-hover">
          <Icon name={icon} className="size-5 text-text-subtle" />
        </span>
      )}
      <h2 className="font-display text-title-md text-text-primary">{title}</h2>
      {description ? (
        <p className="mt-1.5 max-w-md text-body-sm text-text-subtle">
          {description}
        </p>
      ) : null}
      {variant === "no-match" && onClearFilters ? (
        <Button variant="secondary" size="sm" className="mt-4" onClick={onClearFilters}>
          Clear filters
        </Button>
      ) : action ? (
        <div className="mt-4">{action}</div>
      ) : null}
    </div>
  );
}
