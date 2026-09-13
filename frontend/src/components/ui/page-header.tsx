import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/cn";
import { useShellHeader } from "@/components/layout/shell-header";
import { Icon, type IconName } from "@/components/ui/icon";

/**
 * The header every module root shares. Inside the app shell the heading is
 * published to the top bar and `actions` portal into its right-hand slot, so
 * this renders nothing in the content flow: a page keeps calling
 * `<PageHeader title="Assets" />` and the name appears at the top. Outside the
 * shell it falls back to an inline heading.
 *
 * `eyebrow` is accepted for source compatibility but not shown in the shell.
 */
export function PageHeader({
  eyebrow,
  title,
  icon,
  subtitle,
  actions,
}: {
  /** Legacy group label; ignored in the shell. */
  eyebrow?: string;
  title: string;
  /** Module icon, shown in a tile beside the title. */
  icon?: IconName;
  /** One short line under the title. A string, so the published heading only
   *  changes when its text does. */
  subtitle?: string;
  /** The module's own buttons, shown on the title row. */
  actions?: ReactNode;
}) {
  const shell = useShellHeader();
  const setHeading = shell?.setHeading;

  useEffect(() => {
    if (!setHeading) return;
    setHeading({ title, icon, subtitle });
    return () => setHeading(null);
  }, [setHeading, title, icon, subtitle]);

  if (shell) {
    return actions && shell.actionsSlot ? createPortal(actions, shell.actionsSlot) : null;
  }

  return (
    <div className="mb-1 flex flex-wrap items-start justify-between gap-3">
      <div className="flex min-w-0 items-center gap-3">
        {icon ? (
          <span className="grid size-10 shrink-0 place-items-center rounded-md bg-action-accent-tint text-action-accent">
            <Icon name={icon} className="size-5" />
          </span>
        ) : null}
        <div className="min-w-0">
          {eyebrow ? <p className="type-overline">{eyebrow}</p> : null}
          <h1 className={cn("font-display text-heading-lg text-text-primary", eyebrow && "mt-1")}>
            {title}
          </h1>
          {subtitle ? <p className="text-body-sm text-text-subtle">{subtitle}</p> : null}
        </div>
      </div>
      {actions ? (
        <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
      ) : null}
    </div>
  );
}
