import type { ReactNode } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Button, ChartCard, Icon, Skeleton } from "@/components/ui";
import { describeError } from "@/lib/api/describe-error";
import { isForbidden } from "./hooks";

/**
 * The three states every dashboard section shares: bones while it loads, one
 * line and a way back when it fails, and the content when it works. A section
 * that fails says so inside its own frame and never takes the page with it.
 */

export const FOCUS =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent";

/** Inline link used in card actions and empty states. */
export const LINK = `text-body-sm font-semibold text-text-link hover:underline ${FOCUS}`;

export function SectionError({
  error,
  subject,
  onRetry,
}: {
  error: unknown;
  subject: string;
  onRetry: () => void;
}) {
  const failure = describeError(error, subject);
  return (
    <div role="alert" className="flex flex-col items-center gap-2 py-4 text-center">
      <p className="text-body-sm text-text-subtle">{failure.message}</p>
      {failure.retryable ? (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}

export function Settled<T>({
  query,
  subject,
  skeleton,
  children,
}: {
  query: UseQueryResult<T>;
  subject: string;
  skeleton: ReactNode;
  children: (data: T) => ReactNode;
}) {
  if (query.isSuccess) return <>{children(query.data)}</>;
  if (query.isError) {
    return <SectionError error={query.error} subject={subject} onRetry={() => void query.refetch()} />;
  }
  return <div aria-busy="true">{skeleton}</div>;
}

/** A chart card whose body is one query. Hidden outright when the role is refused. */
export function Panel<T>({
  title,
  subject,
  query,
  action,
  className,
  skeleton = <Skeleton className="h-40 w-full" />,
  children,
}: {
  title: string;
  subject: string;
  query: UseQueryResult<T>;
  action?: ReactNode;
  className?: string;
  skeleton?: ReactNode;
  children: (data: T) => ReactNode;
}) {
  if (isForbidden(query.error)) return null;
  return (
    <ChartCard title={title} action={query.isSuccess ? action : undefined} className={className}>
      <Settled query={query} subject={subject} skeleton={skeleton}>
        {children}
      </Settled>
    </ChartCard>
  );
}

/** A headline stat tile whose number is one query: same footprint while loading
 *  and when it fails, so the row never jumps. One query may feed several tiles
 *  (`count`): they load together, and fail as one. */
export function Tile<T>({
  label,
  subject,
  query,
  count = 1,
  children,
}: {
  label: string;
  subject: string;
  query: UseQueryResult<T>;
  count?: number;
  children: (data: T) => ReactNode;
}) {
  if (isForbidden(query.error)) return null;
  if (query.isSuccess) return <>{children(query.data)}</>;
  if (query.isError) {
    const failure = describeError(query.error, subject);
    return (
      <div
        role="alert"
        className="flex min-h-[4.75rem] items-center justify-between gap-3 rounded-lg border border-border bg-surface-primary p-4"
      >
        <span className="min-w-0">
          <span className="block truncate text-body-sm text-text-secondary">{label}</span>
          <span className="block truncate text-caption text-text-subtle">Could not load</span>
        </span>
        {failure.retryable ? (
          <Button variant="secondary" size="sm" className="shrink-0" onClick={() => void query.refetch()}>
            Try again
          </Button>
        ) : null}
      </div>
    );
  }
  return (
    <>
      {Array.from({ length: count }, (_, index) => (
        <Skeleton key={index} className="h-[4.75rem] w-full rounded-lg" />
      ))}
    </>
  );
}

/** A card's "go to the module" link, in the corner the other chart cards use.
 *  Several cards say "All" or "Overview", so `describe` gives each its full
 *  name for a screen reader, which hears links out of context. */
export function ViewAll({ to, label = "All", describe }: { to: string; label?: string; describe?: string }) {
  return (
    <Link to={to} aria-label={describe} className={`inline-flex items-center gap-0.5 rounded-2xs ${LINK}`}>
      {label}
      <Icon name="arrowr" className="size-4" />
    </Link>
  );
}

/** What a card says when its module has nothing yet: one line and the next step. */
export function Empty({ children, to, cta }: { children: ReactNode; to: string; cta: string }) {
  return (
    <div className="py-6 text-center">
      <p className="text-body-sm text-text-subtle">{children}</p>
      <Link to={to} className={`mt-2 inline-block rounded-2xs ${LINK}`}>
        {cta}
      </Link>
    </div>
  );
}
