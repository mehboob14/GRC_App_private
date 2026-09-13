import type { ReactNode } from "react";
import { createPortal } from "react-dom";
import { NavLink } from "react-router-dom";
import { cn } from "@/lib/cn";
import { useShellHeader } from "@/components/layout/shell-header";

export type TabStripItem = {
  /** Route path in link mode, scope value in button mode. */
  id: string;
  label: string;
  /** Link mode only: exact match, for an index route its siblings extend. */
  end?: boolean;
  /** Count badge. This is where a register's deleted summary numbers go. */
  count?: number;
};

/**
 * The one horizontal section strip. Six near-identical copies of this nav
 * existed with four spacing recipes (mb-5 mt-4 / mb-6 mt-4 / mb-5 / mt-5) and
 * two active colours.
 *
 * Two modes, because two consumers switch a local scope rather than a route:
 *   links   - pass nothing else; ids are routes (assets, tasks, frameworks,
 *             vulnerabilities)
 *   buttons - pass `value` + `onSelect`; ids are scope values (documents
 *             active/archived, connections active/available)
 *
 * `aside` is the right-hand slot on the same line, for a single standing figure
 * that has no tab and no facet to live on. It costs no vertical space because
 * the strip row is already there.
 */
export type TabStripVariant = "default" | "bar";

/**
 * `bar` is the wide navigation bar: evenly sized tabs with centred labels, a
 * hover fill, and a heavy underline across the whole active tab, so the
 * current section reads from across the screen.
 */
const tabClass = (isActive: boolean, variant: TabStripVariant) =>
  variant === "bar"
    ? cn(
        "relative -mb-px flex min-w-[8.5rem] shrink-0 items-center justify-center gap-2 whitespace-nowrap px-5 py-3 text-label-md transition-colors duration-150 ease-state",
        "focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-action-accent",
        isActive
          ? "text-text-primary"
          : "text-text-secondary hover:bg-surface-hover hover:text-text-primary",
      )
    : cn(
        "relative -mb-px flex shrink-0 items-center gap-1.5 whitespace-nowrap px-3 py-2.5 text-label-md transition-colors duration-150 ease-state",
        isActive ? "text-action-accent" : "text-text-secondary hover:text-text-primary",
      );

function TabBody({
  tab,
  isActive,
  variant,
}: {
  tab: TabStripItem;
  isActive: boolean;
  variant: TabStripVariant;
}) {
  const bar = variant === "bar";
  return (
    <>
      {tab.label}
      {typeof tab.count === "number" ? (
        <span
          className={cn(
            "tabular rounded-full px-1.5 py-0.5 text-caption font-semibold",
            isActive
              ? bar
                ? "bg-action-accent text-white"
                : "bg-action-accent-tint text-action-accent"
              : "bg-surface-sunken text-text-subtle",
          )}
        >
          {tab.count}
        </span>
      ) : null}
      {isActive ? (
        <span
          className={
            bar
              ? "absolute inset-x-0 -bottom-px h-[3px] rounded-t-sm bg-action-accent"
              : "absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-action-accent"
          }
        />
      ) : null}
    </>
  );
}

export function TabStrip({
  items,
  label,
  value,
  onSelect,
  aside,
  className,
  inline,
  variant = "default",
}: {
  items: readonly TabStripItem[];
  /** aria-label for the nav, e.g. "Asset sections". */
  label: string;
  /** Button mode: the selected id. */
  value?: string;
  /** Button mode: pass to switch a local scope instead of navigating. */
  onSelect?: (id: string) => void;
  aside?: ReactNode;
  className?: string;
  /** Keep the strip in the content flow instead of hoisting it into the top
   *  bar — for record-level tabs on a detail page (which pair with a
   *  DetailHeader), not module-root tabs. */
  inline?: boolean;
  variant?: TabStripVariant;
}) {
  const shell = useShellHeader();

  const inner = (
    <>
      <nav
        className={cn("flex min-w-0 flex-1 overflow-x-auto", variant === "bar" ? "gap-0" : "gap-1")}
        aria-label={label}
      >
        {onSelect
          ? items.map((tab) => {
              const isActive = tab.id === value;
              return (
                <button
                  key={tab.id}
                  type="button"
                  aria-pressed={isActive}
                  onClick={() => onSelect(tab.id)}
                  className={tabClass(isActive, variant)}
                >
                  <TabBody tab={tab} isActive={isActive} variant={variant} />
                </button>
              );
            })
          : items.map((tab) => (
              <NavLink
                key={tab.id}
                to={tab.id}
                end={tab.end}
                className={({ isActive }) => tabClass(isActive, variant)}
              >
                {({ isActive }) => <TabBody tab={tab} isActive={isActive} variant={variant} />}
              </NavLink>
            ))}
      </nav>
      {aside ? (
        <div className="shrink-0 text-caption text-text-subtle">{aside}</div>
      ) : null}
    </>
  );

  // In the shell, the tab strip lives on row 2 of the top bar. Portal into the
  // slot the Topbar owns — no top/bottom margin, the header carries the border.
  if (!inline && shell?.tabsSlot) {
    return createPortal(
      <div className={cn("flex items-center gap-3", className)}>{inner}</div>,
      shell.tabsSlot,
    );
  }
  // In the shell but the slot has not mounted yet: render nothing this frame.
  if (!inline && shell) return null;

  // Outside the shell (safety): the original inline strip.
  return (
    <div className={cn("mb-5 mt-4 flex items-center gap-3 border-b border-border", className)}>
      {inner}
    </div>
  );
}
