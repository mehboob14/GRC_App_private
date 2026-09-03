import { NavLink, useLocation } from "react-router-dom";
import { Badge, BrandMark, Icon, Tooltip } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  FOOTER_ITEMS,
  NAV_SECTIONS,
  type NavItem,
} from "@/components/layout/nav-config";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { WorkspaceSwitcher } from "@/components/layout/workspace-switcher";
import { DARK_MODE_ENABLED } from "@/lib/theme";

const NAV_ROW =
  "flex h-8 w-full items-center gap-2.5 rounded-sm px-2.5 text-left transition-colors duration-80 ease-state";

function NavRow({ item, active }: { item: NavItem; active?: boolean }) {
  // Later-phase module: keyboard-reachable but explicitly not enabled —
  // aria-disabled (not `disabled`) so the tooltip still shows on focus/hover.
  if (item.comingSoon || !item.to) {
    return (
      <Tooltip content={`${item.label} arrives in a later phase`} side="right">
        <button
          type="button"
          aria-disabled
          className={cn(NAV_ROW, "cursor-not-allowed")}
        >
          <Icon name={item.icon} className="size-4 text-text-subtle" />
          <span className="min-w-0 flex-1 truncate text-label-sm text-text-subtle">
            {item.label}
          </span>
          <span className="shrink-0 rounded-full border border-border px-1.5 py-px font-sans text-overline uppercase text-text-subtle">
            Soon
          </span>
        </button>
      </Tooltip>
    );
  }

  return (
    <NavLink
      to={item.to}
      aria-current={active ? "page" : undefined}
      className={cn(
        NAV_ROW,
        active ? "bg-action-accent-tint" : "hover:bg-surface-hover",
      )}
    >
      <Icon
        name={item.icon}
        className={cn(
          "size-4",
          active ? "text-action-primary" : "text-text-secondary",
        )}
      />
      <span
        className={cn(
          "min-w-0 flex-1 truncate text-label-sm",
          active ? "font-semibold text-action-primary" : "text-text-primary",
        )}
      >
        {item.label}
      </span>
      {item.count != null ? (
        <Badge variant={item.countTone === "review" ? "countWarn" : "count"}>
          {item.count}
        </Badge>
      ) : null}
    </NavLink>
  );
}

export function Sidebar() {
  const location = useLocation();
  const settingsActive = location.pathname.startsWith("/settings");

  return (
    <aside
      className="flex h-full w-sidebar shrink-0 flex-col border-r border-border bg-surface-primary px-3 pb-3 pt-4"
      aria-label="Primary"
    >
      <div className="mb-4 flex items-center gap-2.5 px-2 pt-1">
        <BrandMark size={32} />
        <span className="font-display text-heading-sm text-text-primary">
          Verity
        </span>
      </div>

      <nav className="min-h-0 flex-1 overflow-y-auto" aria-label="Modules">
        {NAV_SECTIONS.map((section) => (
          <div key={section.id} className="mb-1">
            <div className="px-2.5 pb-1.5 pt-3">
              {/* Spelled out rather than `type-overline`: that helper lives in
                  the same @layer utilities and is emitted after Tailwind's
                  generated classes, so `text-text-subtle` alongside it loses on
                  source order and the heading stays text-faint — 2.58:1 at
                  10px, well under AA. */}
              <p className="font-sans text-overline uppercase text-text-subtle">
                {section.label}
              </p>
            </div>
            <div className="flex flex-col gap-0.5">
              {section.items.map((item) => (
                <NavRow
                  key={item.id}
                  item={item}
                  active={
                    item.to ? location.pathname.startsWith(item.to) : false
                  }
                />
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="mt-2 border-t border-border pt-2">
        {FOOTER_ITEMS.map((item) => (
          <NavRow
            key={item.id}
            item={item}
            active={
              item.id === "settings"
                ? settingsActive
                : item.to
                  ? location.pathname.startsWith(item.to)
                  : false
            }
          />
        ))}
        {/* Workspace switcher lives at the foot of the rail and opens upward. */}
        <div className="mt-2 flex items-center gap-1.5">
          <div className="min-w-0 flex-1">
            <WorkspaceSwitcher />
          </div>
          {DARK_MODE_ENABLED ? <ThemeToggle /> : null}
        </div>
      </div>
    </aside>
  );
}
