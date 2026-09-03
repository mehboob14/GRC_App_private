import { useEffect, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { useShellHeader } from "@/components/layout/shell-header";

/**
 * The header every module root shares. Inside the app shell the title is
 * published to the top bar (the shell header owns it), so this renders nothing
 * in the content flow — a page keeps calling `<PageHeader title="Assets" />`
 * and the name appears at the top. Outside the shell it falls back to the old
 * inline heading.
 *
 * `eyebrow` is accepted for source compatibility but no longer shown in the
 * shell (the top bar shows the clean module name).
 */
export function PageHeader({
  eyebrow,
  title,
  actions,
}: {
  /** Legacy group label; ignored in the shell. */
  eyebrow?: string;
  title: string;
  actions?: ReactNode;
}) {
  const shell = useShellHeader();
  const setTitle = shell?.setTitle;

  useEffect(() => {
    if (!setTitle) return;
    setTitle(title);
    return () => setTitle(null);
  }, [setTitle, title]);

  if (shell) return null;

  return (
    <div className="mb-1 flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        {eyebrow ? <p className="type-overline">{eyebrow}</p> : null}
        <h1 className={cn("font-display text-heading-lg text-text-primary", eyebrow && "mt-1")}>
          {title}
        </h1>
      </div>
      {actions ? (
        <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
      ) : null}
    </div>
  );
}
