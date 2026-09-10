import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/**
 * The panel chrome every card on the vendor detail page shares.
 *
 * Each feature in this codebase re-declares its own `Panel` rather than using
 * the DS `Card`; this is the vendors copy. It is declared once here instead of
 * once per file because this module has ten panels, not two.
 */
export function Panel({
  title,
  count,
  action,
  description,
  className,
  children,
}: {
  title: string;
  /** A figure that belongs to the title, like a row count. */
  count?: number;
  /** Right-aligned control on the heading row, so the panel's own action costs
   *  no extra vertical space. */
  action?: ReactNode;
  description?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={cn("rounded-lg border border-border bg-surface-primary p-5", className)}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-title-md text-text-primary">
          {title}
          {count !== undefined ? (
            <span className="tabular ml-2 text-body-sm font-normal text-text-subtle">{count}</span>
          ) : null}
        </h2>
        {action}
      </div>
      {description ? (
        <p className="-mt-1 mb-3 text-body-sm text-text-subtle">{description}</p>
      ) : null}
      {children}
    </section>
  );
}

/** A label/value pair. Lives inside a `<dl className="space-y-2.5">`. */
export function Field({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <dt className="text-caption text-text-subtle">{label}</dt>
      <dd className="mt-0.5 text-body-sm text-text-primary">{value}</dd>
    </div>
  );
}

/**
 * What a panel shows when its data source has not been connected.
 *
 * Deliberately not an empty table: an empty table says "nothing found", which
 * is a claim about the vendor. This says the truth, which is that nobody has
 * asked anything yet.
 */
export function NotConnected({ what, why }: { what: string; why: string }) {
  return (
    <div className="rounded-md border border-dashed border-border-strong bg-surface-sunken p-4">
      <p className="text-body-md font-semibold text-text-primary">{what}</p>
      <p className="mt-1 text-body-sm text-text-subtle">{why}</p>
    </div>
  );
}
