import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Icon, type IconName } from "@/components/ui/icon";

/**
 * The header every drill-down page shares: back, title, chips, meta, actions -
 * in that order, always.
 *
 * It exists because the nine detail pages had each grown their own: four back
 * idioms in the app shell (link, button, two-crumb breadcrumb, rotated
 * chevron), two more literal arrow characters in not-found branches, three chip
 * placements (above the title, inline with it, in the action cluster) and two
 * h1 sizes for pages of equal rank.
 *
 * Chips sit BELOW the title. The title is the thing you are looking at; the
 * chips describe it. This is the composition the evidence drawer already uses.
 *
 * `backTo` is optional: TaskDetail renders inside the tasks register as an
 * embedded master/detail pane, where there is nothing to go back to.
 */
export function DetailHeader({
  backTo,
  backLabel,
  icon,
  title,
  chips,
  meta,
  actions,
}: {
  /** Route of the parent surface. Omit when embedded in a pane. */
  backTo?: string;
  /** "Back to <module root label>", worded exactly like the sidebar entry. */
  backLabel?: string;
  /** The record's kind, shown in a tile beside the title. */
  icon?: IconName;
  title: ReactNode;
  /** Status pills, code chips, type badges. Rendered below the title. */
  chips?: ReactNode;
  /** One line of context: owner, hostname, CVE, dates. Below the chips. */
  meta?: ReactNode;
  /** Buttons, or any single node - a detail page may put a stat here. */
  actions?: ReactNode;
}) {
  return (
    <div className="mb-5">
      {backTo && backLabel ? (
        <Link
          to={backTo}
          className="-ml-1.5 mb-3 inline-flex h-7 items-center gap-1 rounded-sm px-1.5 text-label-sm text-text-secondary transition-colors duration-80 ease-state hover:bg-surface-hover hover:text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent"
        >
          <Icon name="arrowleft" className="size-4 shrink-0" aria-hidden />
          {backLabel}
        </Link>
      ) : null}

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 flex-1 items-start gap-3.5">
          {icon ? (
            <span className="grid size-12 shrink-0 place-items-center rounded-md bg-action-accent-tint text-action-accent">
              <Icon name={icon} className="size-6" />
            </span>
          ) : null}
          <div className="min-w-0 flex-1">
            <h1 className="font-display text-heading-lg text-text-primary">{title}</h1>
            {chips ? (
              <div className="mt-2 flex flex-wrap items-center gap-2">{chips}</div>
            ) : null}
            {meta ? <div className="mt-1.5 text-body-sm text-text-subtle">{meta}</div> : null}
          </div>
        </div>
        {actions ? (
          <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
        ) : null}
      </div>
    </div>
  );
}
