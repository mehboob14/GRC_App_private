import type { ReactNode } from "react";

/**
 * The header every settings tab page shares: title, one line of context, and
 * the page's primary action on the right.
 *
 * It exists because People, Groups and Roles had each grown their own: one
 * boxed in a card at `title-md`, one bare at `heading-sm`, and one with no
 * header at all — just a floating button. `SettingsSection` already renders the
 * category name as the page `h1`, so a tab's own title is an `h2` beneath it,
 * matching the rest of settings (Organization, Security).
 */
export function SettingsPageHeader({
  title,
  description,
  count,
  action,
}: {
  title: string;
  description: string;
  /** Optional "N items" prefix on the description line. */
  count?: { value: number; noun: string };
  action?: ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <h2 className="font-display text-heading-sm text-text-primary">{title}</h2>
        <p className="mt-1 text-body-md text-text-secondary">
          {count ? (
            <>
              <span className="tabular font-semibold text-text-primary">
                {count.value}
              </span>{" "}
              {count.noun} ·{" "}
            </>
          ) : null}
          {description}
        </p>
      </div>
      {action ? <div className="flex shrink-0 items-center gap-2">{action}</div> : null}
    </div>
  );
}
