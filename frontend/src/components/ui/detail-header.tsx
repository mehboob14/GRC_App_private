import type { MouseEvent, ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Icon, type IconName } from "@/components/ui/icon";
import { backLabelFor, recordOf } from "@/lib/nav/back-labels";
import { previousEntry } from "@/lib/nav/history-log";

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
 *
 * Back means the page this one was opened from, when this tab saw it: an evidence
 * item opened from a control goes back to that control, and a control opened from
 * a filtered list goes back to the list as it was left. Only a page reached some
 * other way (a bookmark, a new tab) falls back to the parent `backTo` names.
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
  const navigate = useNavigate();
  const here = useLocation();
  const previous = previousEntry();
  const returnTo =
    previous !== null &&
    previous !== here.pathname + here.search &&
    backLabelFor(previous) !== null &&
    // Another tab of this same record is not where Back goes.
    (recordOf(previous) === null || recordOf(previous) !== recordOf(here.pathname))
      ? previous
      : null;

  // A plain click goes back in the history, so the page returns as it was left. A
  // click with a modifier (a new tab) keeps the link's own address.
  function goBack(event: MouseEvent<HTMLAnchorElement>) {
    const plain =
      event.button === 0 &&
      !event.metaKey &&
      !event.ctrlKey &&
      !event.shiftKey &&
      !event.altKey;
    if (returnTo !== null && plain && !event.defaultPrevented) {
      event.preventDefault();
      navigate(-1);
    }
  }

  return (
    <div className="mb-5">
      {backTo && backLabel ? (
        <Link
          to={returnTo ?? backTo}
          onClick={goBack}
          className="-ml-1.5 mb-3 inline-flex h-7 items-center gap-1 rounded-sm px-1.5 text-label-sm text-text-secondary transition-colors duration-80 ease-state hover:bg-surface-hover hover:text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent"
        >
          <Icon name="arrowleft" className="size-4 shrink-0" aria-hidden />
          {returnTo !== null ? backLabelFor(returnTo) : backLabel}
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
